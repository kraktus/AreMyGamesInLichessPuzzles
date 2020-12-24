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

TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH")

HEADER = {"Authorization": f"Bearer {TOKEN}"}
GAME_ID_REGEX = re.compile(r'\[Site "https://lichess\.org/(.*)"\]') #from the player download
PLAYER_REGEX = re.compile(r'\[(White|Black) "(.*)"\]')
LI = "https://lichess.org/"
LIT = LI + "training/"

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
    with requests.post("https://lichess.org/games/export/_ids?moves=false", headers=HEADER, data=",".join(games), stream=True) as r:
        if r.status_code != 200:
            print(f"\nError, http code: {r.status_code}")
            time.sleep(65) #Respect rate-limits!
        for line in r.iter_lines():
            #print(line)
            #print(line.decode("utf-8"))
            m = PLAYER_REGEX.match(line.decode("utf-8"))
            if m:
                if m.group(1) == "White":
                    res += games[nb_processed] + " " + m.group(2)
                else:
                    res += " " + m.group(2) + "\n"
                    print(f"\r{games_dl + nb_processed} games downloaded, {(time.time() - dep):.2f}s",end="")
                    nb_processed += 1
    return res

def compute() -> List[Row]:
    dic = {}
    game_to_puzzle_id = game_puzzle_id()
    #print(game_to_puzzle_id)
    with open("puzzle_games.txt", "r") as file_input:
        for line in file_input:
            args = line.split() # game id, white player, black player
            for player in args[1:]: # first arg is game id
                add_to_list_of_values(dic, player, game_to_puzzle_id[args[0]])
    
    npp = lambda x: len(x[1]) # Number of Puzzles of the Player
    #print(dic)
    sorted_tuple = sorted(dic.items(),key=npp,reverse=True)
    l_row = []
    rank = 1
    nb_puzzles = npp(sorted_tuple[0])
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



