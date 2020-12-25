#!/usr/local/bin/python3
#coding: utf-8

"""
Generate a "leaderboard" of the players according to the number of puzzles generated from their games
"""

import csv
import json
import requests
import os
import re
import time

from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List

#############
# Constants #
#############

load_dotenv()

DB_PATH = os.getenv("DB_PATH")

GAME_ID_REGEX = re.compile(r'\[Site "https://lichess\.org/(.*)"\]') #from the player download
PLAYER_REGEX = re.compile(r'\[(White|Black) "(.*)"\]')

###########
# Classes #
###########

@dataclass
class Row:
    rank: int
    player: str
    l_puzzles: List[str]

#############
# Functions #
#############

def add_to_list_of_values(dic: "Dict[A, List[B]]", key: "A", val: "B") -> None:
    l_elem = dic.get(key)
    if l_elem is None:
        dic[key] = [val]
    else:
        l_elem.append(val)

def download_puzzles_games(starting_line: int = 0) -> Dict[str, str]:
    #Fields for the new db: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl
    with open(DB_PATH, newline='') as csvfile:
        puzzles = csv.reader(csvfile, delimiter=',', quotechar='|')
        chunk = 0 #games can be dl 500 at a time with a token
        dep = time.time()
        games = []
        with open("puzzle_games.txt", "a") as output:
            for puzzle in puzzles:
                if chunk < starting_line: continue
                if chunk % 300 == 0:
                    res = req(games, chunk - 300, dep)
                    output.write(res)
                    games = []
                game_id = puzzle[-1].split('/')[3].partition('#')[0] #ex: https://lichess.org/Fr7rv4jo/black#98 or https://lichess.org/JbCsF5hm#43
                games.append(game_id)
                
                chunk += 1
    return dic

def update():
    game_to_puzzle_id = game_puzzle_id()
    l_games_dl = list_games_already_dl()
    for game_id in l_games_dl:
        if game_to_puzzle_id.pop(game_id, None) is None:
            print(f"game {game_id} was dl but not in the puzzle db, Error")
    # Only games in the db not dl are left in the dic
    games_not_dl = list(game_to_puzzle_id.keys())
    print(f"{len(games_not_dl)} games left to be dl, expecting {len(games_not_dl)/20:.2f}s")
    c = 0
    dep = time.time()
    with open("puzzle_games.txt", "a") as output:
        for i in range(0, len(games_not_dl), 300): #dl games 300 at a time
            res = req(games_not_dl[i:i+300],c,dep)
            output.write(res)
            c += 300

def list_games_already_dl() -> List[str]:
    l = []
    with open("puzzle_games.txt", "r") as file_input:
        for line in file_input:
            l.append(line.split()[0])
    return l

def game_puzzle_id() -> Dict[str, str]:
    """
    returns a dic game_id -> puzzle_id
    A game can only produce at most one puzzle
    """
    dic = {}
    #Fields for the new db: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl
    with open(DB_PATH, newline='') as csvfile:
        puzzles = csv.reader(csvfile, delimiter=',', quotechar='|')
        for puzzle in puzzles:
            game_id = puzzle[-1].split('/')[3].partition('#')[0]
            dic[game_id] = puzzle[0]
    return dic
                
def req(games: List[str], games_dl: int, dep: float) -> str:
    res = ""
    nb_processed = 0
    current_game_id = ""
    with open("raw_response.txt", "a") as raw_response:
        raw_response.write("-"*20 + f"req requested at {time.time()}" + "-"*20 + "\n")
        with requests.post("https://lichess.org/games/export/_ids?moves=false", data=",".join(games), stream=True) as r:
            if r.status_code != 200:
                print(f"\nError, http code: {r.status_code}")
                time.sleep(65) #Respect rate-limits!
            for line in r.iter_lines():
                decoded_line = line.decode("utf-8")
                raw_response.write(decoded_line + "\n")
                m_game = GAME_ID_REGEX.match(decoded_line)
                if m_game:
                    current_game_id = m_game.group(1)

                m_player = PLAYER_REGEX.match(decoded_line)
                if m_player:
                    if m_player.group(1) == "White":
                        res += current_game_id + " " + m_player.group(2)
                    else:
                        res += " " + m_player.group(2) + "\n"
                        print(f"\r{games_dl + nb_processed} games downloaded, {(time.time() - dep):.2f}s",end="")
                        nb_processed += 1
    return res

def compute() -> List[Row]:
    dic = {}
    game_to_puzzle_id = game_puzzle_id()
    with open("puzzle_games.txt", "r") as file_input:
        for line in file_input:
            args = line.split() # game id, white player, black player
            for player in args[1:]: # first arg is game id
                add_to_list_of_values(dic, player, game_to_puzzle_id[args[0]])
    
    # Sort the players
    npp = lambda x: len(x[1]) # Number of Puzzles of the Player
    sorted_tuple = sorted(dic.items(),key=npp,reverse=True)
    l_row = []
    rank = 1
    nb_puzzles = npp(sorted_tuple[0])
    # Add rank to each player
    for row in sorted_tuple:
        if npp(row) != nb_puzzles:
            rank += 1
            nb_puzzles = npp(row)
        l_row.append(Row(rank=rank,player=row[0],l_puzzles=row[1]))
    return l_row

def save_csv(l_row: List[Row]) -> None:
    with open("leaderboard.csv", "w") as csvfile:
        fieldnames = ['rank', 'player', 'number_puzzles_generated', 'list_puzzle_ids']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in l_row:
            writer.writerow({'rank': row.rank, 'player': row.player, 'number_puzzles_generated': len(row.l_puzzles), 'list_puzzle_ids':" ".join(row.l_puzzles)})

def check_sanity():
    """
    Check if a game is present twice or more
    """
    s = set()
    print("checking sanity of the games dl...")
    with open("puzzle_games.txt", "r") as file_input:
        for line in file_input:
            game_id = line.split()[0]
            if game_id in s:
                print(game_id)
            else:
                s.add(game_id)
    # It was sane!

def main():
    print(f"Creating leaderboard")
    if not Path(f"puzzle_games.txt").exists():
        print("Game ids not stored, downloading...")
        download_puzzles_games()
        print("\nDownload finished")
    else:
        print("Game ids found, updating...")
        update()
    print(f"Computing")
    dic = compute()
    print("saving to leaderboard.csv")
    save_csv(dic)

########
# Main #
########

if __name__ == "__main__":
    print('#'*80)
    main()
    #check_sanity()
    #print("\n"+req(["gX1AOHfA", "9F9G6yiK", "zJy6vEgo"], 1, time.time()))
    #bM5DTJxW OGNYN scarface2015

