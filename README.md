# Players "leaderboard" in term of puzzles generated

It's the file [`leaderboard.csv`](https://github.com/kraktus/AreMyGamesInLichessPuzzles/blob/master/leaderboard.csv).

[`puzzle_games.txt`](https://github.com/kraktus/AreMyGamesInLichessPuzzles/blob/master/puzzle_games.txt) although being heavy, is included to avoid fetching the games again on lichess' side (\~9h).

**Caveat** Those 18 games are currently not included in the leaderboard as they can't be fecth from lichess API ([issue](https://github.com/ornicar/lila/issues/7786)): `['7LGG4sw0', 'vrDMUTwS', 'mQcbOvRL', '8yK1LBKn', 'z1XDezKL', 'lbKzyQRK', 'a3surdtD', 'AQwp1CqI', '73jh5PrA', 'uxfBjPUq', 'q2kkxMNh', 'QSxPkb3C', 'BN5ih6aM', 'cy9XI8X2', 'tzfJtg24', 'MESZ0YUr', 'VFyzVZWD', 'wRhpk1WE']`

## Installation

Create an `.env` file in the current directory and add `DB_PATH=YOUR/PATH/TO/LICHESS/PUZZLES/DB`), the puzzle V2 database can be downloaded [here](https://database.lichess.org/#puzzles).

Install the python dependencies (`pip3 install -r requirements.txt`)