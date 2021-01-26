from aiohttp import web
import aiohttp_jinja2
import jinja2
import pathlib
import re


BASE_DIR = pathlib.Path(__file__).parent.absolute()
print(BASE_DIR)
TEMPLATE_PATH = str(BASE_DIR / 'templates')
with open("leaderboard.csv") as leaderboard_file:
    LEADERBOARD_RECORDS = leaderboard_file.read().split("\n")[1:]


def getpuzzles_for(username):
    puzzle_matcher = re.compile(f"([0-9]+),({username}),([0-9]+),(.*)", re.I)
    for record in LEADERBOARD_RECORDS:
        match = puzzle_matcher.match(record)
        if match:
            [rank, username, num, ids] = match.groups()
            return {
                "rank": rank,
                "username": username,
                "num": num,
                "ids": ids.split(" ")
            }
    return None


@aiohttp_jinja2.template('index.jinja2')
async def handle(request):
    username = request.rel_url.query.get('getpuzzles', None)
    result = None
    if username:
        result = getpuzzles_for(username)
    return {
        "username": username,
        "welcome": "Welcome to amgilp !",
        "getpuzzles": result
    }


def init_func(argv=None):
    app = web.Application()

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(TEMPLATE_PATH))
    app.add_routes([web.get('/', handle), web.get('/{name}', handle)])
    return app


if __name__ == '__main__':
    web.run_app(init_func())
