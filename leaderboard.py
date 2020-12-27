#!/usr/local/bin/python3
#coding: utf-8

"""
Generate a "leaderboard" of the players according to the number of puzzles generated from their games
"""

from __future__ import annotations

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

GAMES_DL_PATH = "puzzle_games.txt"
LEADERBOARD_PATH = "leaderboard.csv"

###########
# Classes #
###########

@dataclass
class Row:
    rank: int
    player: str
    l_puzzles: List[str]

class Downloader:

    def __init__(self, f: FileHandler):
        self.dep = time.time()
        self.games_dl = 0
        self.file_handler = f

    def tl(self):
        """time elapsed"""
        return time.time() - self.dep

    def update(self):
        game_to_puzzle_id = self.file_handler.game_puzzle_id()
        l_games_dl = self.file_handler.list_games_already_dl()
        print(f"{self.tl():.2f}s to check current state")
        for game_id in l_games_dl:
            if game_to_puzzle_id.pop(game_id, None) is None:
                print(f"game {game_id} was dl but not in the puzzle db, Error")
        # Only games in the db not dl are left in the dic
        #print(game_to_puzzle_id)
        games_not_dl = list(game_to_puzzle_id.keys())
        if len(games_not_dl) < 100:
            print("Most likely these games can't be fetch by lichess API as aborted by server:\n"
                f"{games_not_dl}\n"
                "To be sure, run the script a second time")
        print(f"{len(games_not_dl)} games left to be dl, expecting {(self.tl() + len(games_not_dl)/20):.2f}s")
        with open(GAMES_DL_PATH, "a") as output:
            for i in range(0, len(games_not_dl), 300): #dl games 300 at a time
                #print(i)
                #print(games_not_dl[i:i+300])
                res = self.req(games_not_dl[i:i+300])
                #print(res)
                output.write(res)

    def req(self, games: List[str]) -> str:
        res = ""
        current_game_id = ""
        with open("raw_response.txt", "a") as raw_response:
            raw_response.write("-"*20 + f"req requested at {time.time()}" + "-"*20 + "\n") # At a point I should just start logging but...
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
                            print(f"\r{self.games_dl} games downloaded, {self.tl():.2f}s",end="")
                            self.games_dl += 1
        return res

class FileHandler:

    def list_games_already_dl(self) -> List[str]:
        l = []
        try:
            with open(GAMES_DL_PATH, "r") as file_input:
                for line in file_input:
                    l.append(line.split()[0])
        except FileNotFoundError:
            print(f"{GAMES_DL_PATH} not found, 0 games dl")
        return l

    def game_puzzle_id(self) -> Dict[str, str]:
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

    def compute(self) -> List[Row]:
        dic = {}
        game_to_puzzle_id = self.game_puzzle_id()
        with open(GAMES_DL_PATH, "r") as file_input:
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

    def save_csv(self, l_row: List[Row]) -> None:
        with open(LEADERBOARD_PATH, "w") as csvfile:
            fieldnames = ['rank', 'player', 'number_puzzles_generated', 'list_puzzle_ids']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in l_row:
                writer.writerow({'rank': row.rank, 'player': row.player, 'number_puzzles_generated': len(row.l_puzzles), 'list_puzzle_ids':" ".join(row.l_puzzles)})

    def check_sanity(self):
        """
        Check if a game is present twice or more
        """
        s = set()
        sanity = True
        print("checking sanity of the games dl...")
        with open(GAMES_DL_PATH, "r") as file_input:
            for line in file_input:
                game_id = line.split()[0]
                if game_id in s:
                    print(game_id)
                    sanity = False
                else:
                    s.add(game_id)

        if sanity:
            print("games dl are sane")
        else:
            raise Exception("games dl not sane, one's been dl more than once")

#############
# Functions #
#############

def add_to_list_of_values(dic: "Dict[A, List[B]]", key: "A", val: "B") -> None:
    l_elem = dic.get(key)
    if l_elem is None:
        dic[key] = [val]
    else:
        l_elem.append(val)

def main():
    print(f"Creating leaderboard")
    file_handler = FileHandler()
    file_handler.check_sanity()
    dler = Downloader(file_handler)
    dler.update()
    print(f"Computing")
    dic = file_handler.compute()
    print("saving to leaderboard.csv")
    file_handler.save_csv(dic)

########
# Main #
########

if __name__ == "__main__":
    print('#'*80)
    main()

