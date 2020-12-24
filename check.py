#!/usr/local/bin/python3
#coding: utf-8

"""
Check if there are games from a selected user that ended up generating puzzles
"""

import csv
import requests
import os
import re
import time

from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List

#############
# Constants #
#############

load_dotenv()

TOKEN = os.getenv("TOKEN")
NAME = os.getenv("NAME")
DB_PATH = os.getenv("DB_PATH")

HEADER = {"Authorization": f"Bearer {TOKEN}"}
SOURCE_PATH = f"players_games/{NAME}.txt"
GAME_ID_REGEX = re.compile(r'\[Site "https://lichess\.org/(.*)"\]') #from the player download
LI = "https://lichess.org/"
LIT = LI + "training/"

#############
# Functions #
#############

def add_to_list_of_values(dic: "Dict[A, List[B]]", key: "A", val: "B") -> None:
    l_elem = dic.get(key)
    if l_elem is None:
        dic[key] = [val]
    else:
        l_elem.append(val)

def puzzle_id_by_game() -> Dict[str, List[str]]:
    dic: Dict[str, str] = {}
    #Fields for the new db: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl
    with open(DB_PATH, newline='') as csvfile:
        puzzles = csv.reader(csvfile, delimiter=',', quotechar='|')
        for puzzle in puzzles:
            game_id = puzzle[-1].split('/')[3].partition('#')[0] #ex: https://lichess.org/Fr7rv4jo/black#98 or https://lichess.org/JbCsF5hm#43
            #print(game_id)
            dic[game_id] = puzzle[0]

    return dic

def download_user_games():
    with open(SOURCE_PATH, "w") as file:
        with requests.get(f"https://lichess.org/api/games/user/{NAME}?rated=true&moves=false", headers=HEADER, stream=True) as r:
            if r.status_code != 200:
                raise Exception(f"Error, http code: {r.status_code}")
            games = 1
            dep = time.time()
            print()
            for line in r.iter_lines():
                m = GAME_ID_REGEX.match(line.decode("utf-8"))
                #print(line)
                #print(line.decode("utf-8"))
                if m:
                    file.write(m.group(1)+'\n')
                    print(f"\r{games} games downloaded, {(time.time() - dep):.2f}s",end="")
                    games += 1
            print()

def normalise():
    with open(f"{NAME}.txt", "r") as file:
        n = 8
        line = file.read()
        normalised = [line[i:i+n] for i in range(0, len(line), n)]
    with open(f"{NAME}.txt", "w") as file:
        file.write("\n".join(normalised))

def main():
    print(f"Looking for user {NAME}")
    if not Path(SOURCE_PATH).exists():
        print("Game ids not stored, downloading...")
        download_user_games()
        print("Download finished")
    dic = puzzle_id_by_game()
    tt = 0
    with open(SOURCE_PATH, "r") as file:
        for line in file:
            sline = line.strip(' \n')
            #print(f"passing through the file: {sline}")
            if sline in dic:
                #print(f"game {sline} generated puzzle {dic[sline]}")
                print(f"puzzle {LIT + dic[sline]}")
                tt += 1
    print(f"{tt} puzzles generated from this user")

########
# Main #
########


if __name__ == "__main__":
    print('#'*80)
    main()