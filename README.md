# Players "leaderboard" in term of puzzles generated

It's the file [`leaderboard.csv`](https://github.com/kraktus/AreMyGamesInLichessPuzzles/blob/master/leaderboard.csv).

[`puzzle_games.txt`](https://github.com/kraktus/AreMyGamesInLichessPuzzles/blob/master/puzzle_games.txt) although being heavy, is included to avoid fecthing the games again on lichess' side (~9h).


## Installation

Create an `.env` file in the current directory and add `DB_PATH=YOUR/PATH/TO/LICHESS/PUZZLES/DB`), the puzzle V2 database can be downloaded [here](https://database.lichess.org/#puzzles).

Install the python dependencies (`pip3 install -r requirements.txt`)