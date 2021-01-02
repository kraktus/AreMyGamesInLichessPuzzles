#!/usr/local/bin/python3
#coding: utf-8

"""
Generate a "leaderboard" of the players according to the number of puzzles generated from their games
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import logging.handlers
import requests
import os
import re
import time
import sys

from argparse import RawTextHelpFormatter
from copy import deepcopy
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Callable, Dict, List, Iterator, Set

#############
# Constants #
#############

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
GAMES_DL_PATH = "puzzle_games.txt"
LEADERBOARD_PATH = "leaderboard.csv"
LOG_PATH = "amgilp.log"

GAME_ID_REGEX = re.compile(r'\[Site "https://lichess\.org/(.*)"\]') #from the player download
PLAYER_REGEX = re.compile(r'\[(White|Black) "(.*)"\]')

GAMES_BY_ID_API = "https://lichess.org/games/export/_ids?moves=false"
ABORTED_GAME_BY_ID = "https://lichess.org/game/export/{}?moves=false&opening=false"



########
# Logs #
########

# Are My Games In Lichess Puzzles
log = logging.getLogger("amgilp")
log.setLevel(logging.DEBUG)
format_string = "%(asctime)s | %(levelname)-8s | %(message)s"

# 125000000 bytes = 1Gb
handler = logging.handlers.RotatingFileHandler(LOG_PATH, maxBytes=125000000, backupCount=3, encoding="utf8")
handler.setFormatter(logging.Formatter(format_string))
handler.setLevel(logging.DEBUG)
log.addHandler(handler)

handler_2 = logging.StreamHandler(sys.stdout)
handler_2.setFormatter(logging.Formatter(format_string))
handler_2.setLevel(logging.INFO)
log.addHandler(handler_2)

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
        games_not_dl = self.file_handler.get_games_not_dl()
        log.info(f"{len(games_not_dl)} games left to be dl, expecting {(self.tl() + len(games_not_dl)/20):.2f}s")
        with open(GAMES_DL_PATH, "a") as output:
            for i in range(0, len(games_not_dl), 300): #dl games 300 at a time
                res = self.req(",".join(games_not_dl[i:i+300]), "POST", GAMES_BY_ID_API)
                output.write(res)

        # To fetch information from games aborted by the server, need to use another endpoint
        games_aborted_by_server = self.file_handler.get_games_not_dl()
        with open(GAMES_DL_PATH, "a") as output:
            log.info(f"{len(games_aborted_by_server)} Games aborted by the server: {games_not_dl}")
            for game_id in games_aborted_by_server:
                res = self.req(method="GET", endpoint=ABORTED_GAME_BY_ID.format(game_id), data="")
                output.write(res)

    def req(self, data: str, method: str, endpoint: str) -> str:
        res = ""
        current_game_id = ""
        with requests.request(method=method, url=endpoint, data=data, stream=True) as r:
            if r.status_code != 200:
                log.error(f"\nError, http code: {r.status_code}")
                time.sleep(65) #Respect rate-limits!
            res += self.handle_streamed_response(r.iter_lines())
        return res

    def handle_streamed_response(self, lines: Iterator[str]) -> str:
        res = ""
        current_game_id = ""
        for line in lines:
            decoded_line = line.decode("utf-8")
            log.debug(decoded_line)
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

    game_to_puzzle_id: Option[Dict[str, str]] = None

    def list_games_already_dl(self) -> List[str]:
        l = []
        try:
            with open(GAMES_DL_PATH, "r") as file_input:
                for line in file_input:
                    l.append(line.split()[0])
        except FileNotFoundError:
            log.info(f"{GAMES_DL_PATH} not found, 0 games dl")
        return l

    def game_puzzle_id(self, force_refresh = False) -> Dict[str, str]:
        """
        returns a dic game_id -> puzzle_id
        A game can only produce at most one puzzle
        """
        if self.game_to_puzzle_id is not None and not force_refresh:
            return deepcopy(self.game_to_puzzle_id)
        dic = {}
        #Fields for the new db: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl
        with open(DB_PATH, newline='') as csvfile:
            puzzles = csv.reader(csvfile, delimiter=',', quotechar='|')
            for puzzle in puzzles:
                game_id = puzzle[-1].split('/')[3].partition('#')[0]
                dic[game_id] = puzzle[0]
        self.game_to_puzzle_id = deepcopy(dic)
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
        log.info("checking sanity of the games dl...")
        with open(GAMES_DL_PATH, "r") as file_input:
            for line in file_input:
                game_id = line.split()[0]
                if game_id in s:
                    log.error(f"{game_id} present more than once")
                    sanity = False
                else:
                    s.add(game_id)

        if sanity:
            log.info("games dl are sane")
        else:
            raise Exception("games dl not sane, one's been dl more than once")

    def get_games_not_dl(self) -> List[str]:
        game_to_puzzle_id = self.game_puzzle_id()
        l_games_dl = self.list_games_already_dl()
        sane = True
        for game_id in l_games_dl:
            if game_to_puzzle_id.pop(game_id, None) is None:
                log.error(f"game {game_id} was dl but not in the puzzle db anymore")
                sane = False
        if not sane:
            raise Exception("Some games linked to legacy puzzles were detected, run `clean` command before attempting again")
        return list(game_to_puzzle_id.keys())

    def get_legacy_games(self) -> List[str]:
        l = []
        game_to_puzzle_id = self.game_puzzle_id()
        l_games_dl = self.list_games_already_dl()
        for game_id in l_games_dl:
            if game_to_puzzle_id.pop(game_id, None) is None:
                l.append(game_id)
        log.info(f"{len(l)} games will be removed: {l}")
        return l

    def remove_games(self, l_game_id: Set[str]) -> None:
        """Remove all `l_game_id` games id from `GAMES_DL_PATH`"""
        temp_name = "temporary_file.txt"
        with open(GAMES_DL_PATH, 'r') as file_input, open(temp_name, 'w') as temp_file:
            for line in file_input:
                game_id = line.split()[0]
                if not game_id in l_game_id:
                    temp_file.write(f"{line}")
        os.replace(temp_name, GAMES_DL_PATH) # temp_name -> GAMES_DL_PATH

#############
# Functions #
#############

def add_to_list_of_values(dic: "Dict[A, List[B]]", key: "A", val: "B") -> None:
    l_elem = dic.get(key)
    if l_elem is None:
        dic[key] = [val]
    else:
        l_elem.append(val)

def create_leaderboard() -> None:
    """
    Fetch games from Lichess, compute the leaderboard and save it under `LEADERBOARD_PATH`
    """
    log.info(f"Creating leaderboard")
    file_handler = FileHandler()
    file_handler.check_sanity()
    dler = Downloader(file_handler)
    dler.update()
    log.info(f"Computing")
    dic = file_handler.compute()
    log.info("saving to leaderboard.csv")
    file_handler.save_csv(dic)

def remove_games_no_longer_db() -> None:
    """
    Remove all games linked to puzzles (from `GAMES_DL_PATH`) that don't exists in `DB_PATH` anymore, which means they've been deleted on Lichess.
    """
    log.info("Removing games linked to legacy puzzles")
    file_handler = FileHandler()
    games = file_handler.get_legacy_games()
    file_handler.remove_games(games)
    log.info("done")

def doc(dic: Dict[str, Callable[..., Any]]) -> str:
    """Produce documentation for every command based on doc of each function"""
    doc_string = ""
    for name_cmd, func in dic.items():
        doc_string += f"{name_cmd}: {func.__doc__}\n\n"
    return doc_string

def main():
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    commands = {
    "create": create_leaderboard,
    "clean": remove_games_no_longer_db
    }
    parser.add_argument("command", choices=commands.keys(), help=doc(commands))
    args = parser.parse_args()
    commands[args.command]()

########
# Main #
########

if __name__ == "__main__":
    print('#'*80)
    main()

