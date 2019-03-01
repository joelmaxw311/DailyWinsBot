#!/usr/bin/env python -u
# Work with Python 3.6
import random
import time
import datetime
import asyncio
import aiohttp
import subprocess
import json
import discord
from discord import Game
from discord.ext.commands import Bot

import sys
import os
import re

BOT_PREFIX = ("?", "!")

save_lock = False
plot_queue = []
db_path = 'db/'
database_path = db_path + 'database.txt'
history_path = db_path + 'history.txt'

winsDB = {}
history = []

client = Bot(command_prefix=BOT_PREFIX)


def check_db_path():
    if not os.path.exists(db_path):
        os.makedirs(db_path)


def load_database():
    global database_path
    db = {}
    try:
        check_db_path()
        f = open(database_path, 'r')
        db = json.loads(f.read())
        f.close()
        print("Loaded database from file")
    except:
        print("Failed to load database from file")
    return db


def load_history():
    global history_path
    hist = []
    try:
        f = open(history_path, 'r')
        hist = json.loads(f.read())
        f.close()
        print("Loaded history from file")
    except:
        print("Failed to load history from file")
    return hist


def load_all_saved_data():
    global winsDB
    global history
    winsDB = load_database()
    history = load_history()


def plot_configuration(max_wins, players, data_path=''):
    config = """# gnuplot script file for wins per day
#!/usr/bin/gnuplot
reset
set terminal png

set xdata time
set timefmt "%m/%d/%Y"
set format x "%m/%d" """
    config += """
set xlabel "Date (month/day)"
set ylabel "Wins"

set xrange [*:*]
set yrange [0:%s]
set xtics 86400
set ytics 1 """ % (max_wins + 1)
    config += """
set title "Daily Wins"
set key below
set grid
plot """
    plots = []
    for player in players:
        plots.append('"%s.csv" using 1:2 title "%s" with linespoints' % (data_path + player, player))
    config += ', '.join(plots)
    return config


async def generate_plot(context, players):
    plots_path = "plot/"
    data_path = plots_path + "data/"
    config_path = plots_path + "plot.gp"
    result_path = plots_path + "plot.png"
    if not os.path.exists(plots_path):
        os.makedirs(plots_path)
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    # compile wins per day for selected players, and find the highest wins per day for any player
    max_wins = 0
    pattern = re.compile("^[A-Za-z0-9 ]+$")
    for player in players:
        if pattern.match(player):
            data = {}
            # group win count entries by date
            for entry in history:
                if entry['player'] == player:
                    data[entry['date']] = data.get(entry['date'], 0) + entry['wins']
            # write wins/date for this player to a .csv file
            f = open(data_path + player + '.csv', 'w')
            for date, wins in data.items():
                f.write(', '.join((date, str(wins))) + '\n')
            f.close()
            # find max_wins
            max_wins = max(max_wins, *data.values())
    # write gnuplot configuration to a .gp file
    config = plot_configuration(max_wins, players, data_path)
    f = open(config_path, 'w')
    f.write(config)
    f.close()
    # generate plot with gnuplot and redirect the output to a .png file
    f = open(result_path, "w")
    status = subprocess.call(["gnuplot", config_path], stdout=f)
    f.close()
    # post the image to Discord
    if status == 0:
        await client.send_file(context.message.channel, result_path)
    else:
        await client.send_message(context.message.channel, 'Whoops! There was a problem generating the plot.')


async def plot_wins(context, players):
    plot_queue.append((context, players))
    if len(plot_queue) > 1:
        return
    while len(plot_queue) > 0:
        ctx, plrs = plot_queue.pop()
        await generate_plot(ctx, plrs)


def is_status_running():
    if not os.path.exists('service'):
        return False
    f = open('service', 'r')
    status = f.read()
    f.close()
    return status == 'running'


def write_status(status):
    f = open('service', 'a')
    f.write(status)
    f.close()


def status_run():
    write_status('running')


def status_exit():
    write_status('exit')


async def status_test():
    f = open('service', 'r')
    status = f.read()
    if status == 'exit':
        print('Logging out...')
        client.close()
    f.close()


async def save_database():
    global save_lock
    global database_path
    global history_path
    if not save_lock:
        save_lock = True
        f = open(database_path, 'w')
        f.write(json.dumps(winsDB, indent=4, sort_keys=True))
        f.close()
        f = open(history_path, "w")
        f.write(json.dumps(history, indent=4, sort_keys=True))
        f.close()
        save_lock = False


def log_change(user, delta, players):
    d = datetime.datetime.today()
    for player in players:
        entry = {
            'user': user.name + '#' + user.discriminator,
            'wins': delta,
            'date': '%s/%s/%s' % (d.month, d.day, d.year),
            'player': player,
            'squad': sorted(players)
        }
        history.append(entry)
    save_database()
    

async def addWins(context, count, *players):
    if count < 0:
        print('Cannot add negative wins')
        return
    log_change(context.message.author, count, players)
    for player in players:
        oldval = winsDB.get(player, 0)
        winsDB[player] = oldval + count
        print("Added " + str(count) + " wins for " + player + ':')
        await client.send_message(context.message.channel, "Added " + str(count) + " wins for " + player)
    client.loop.create_task(save_database())
    return


async def subtractWins(context, count, *players):
    if count < 0:
        print('Cannot subtract negative wins')
        return
    for player in players:
        val = winsDB.get(player, 0)
        if val < count:
            print(str(player) + 'does not have enough wins to subtract ' + str(count))
            return
    log_change(context.message.author, -count, players)
    for player in players:
        oldval = winsDB.get(player, 0)
        winsDB[player] = oldval - count
        print("Subtracted " + str(count) + " wins from " + player)
        await client.send_message(context.message.channel, "Subtracted " + str(count) + " wins from " + player)
    client.loop.create_task(save_database())
    return


async def list_servers():
    await client.wait_until_ready()
    while not client.is_closed:
        print("Current servers:")
        for server in client.servers:
            print(server.name)
        await asyncio.sleep(600)


async def check_status():
    status_run()
    await client.wait_until_ready()
    while not client.is_closed:
        await status_test()
        await asyncio.sleep(5)


def get_role(server, role_id):
    for each in server.roles:
        if each.id == role_id:
            return each
    return None


def stop_bot():
    status_exit()
    client.close()


def start_bot(token):
    load_all_saved_data()
    if is_status_running():
        print("WARNING: Bot may already be running in another process")
    client.loop.create_task(list_servers())
    client.loop.create_task(check_status())
    client.run(token)


@client.command(name='addwins',
                description="Add wins for a list of players.",
                brief="Edit the wins database",
                aliases=['add'],
                pass_context=True)
async def cmd_addwins(context, count, *players):
    count = int(count)
    if count > 0:
        await addWins(context, count, *players)
    elif count < 0:
        await subtractWins(context, count, *players)
    else:
        await client.send_message(context.message.channel, "Cannot add 0 wins.")


@client.command(name='subwins',
                description="Subtract wins for a list of players.",
                brief="Edit the wins database",
                aliases=['sub'],
                pass_context=True)
async def cmd_subwins(context, count, *players):
    count = int(count)
    if count < 0:
        await addWins(context, count, *players)
    elif count > 0:
        await subtractWins(context, count, *players)
    else:
        await client.send_message(context.message.channel, "Cannot remove 0 wins.")


@client.command(name='listwins',
                description="List wins for a list of players.",
                brief="View the wins database",
                aliases=['viewwins', 'showwins', 'list', 'view'],
                pass_context=True)
async def cmd_listwins(context, *players):
    if len(players) == 0:
        players = winsDB.keys()
    message = '```'
    message += "%-20s %-6s\n" % ('Player', 'Wins')
    for player in players:
        message += " %-20s %-6s\n" % (player, winsDB[player])
    message += '```'
    await client.send_message(context.message.channel, message)


@client.command(name='history',
                description="List wins for a list of players.",
                brief="View the wins database",
                aliases=['winlog'],
                pass_context=True)
async def cmd_history(context, player):
    message = '```History of wins for ' + player + '\n'
    message += "%-6s %-9s %-20s %s\n" % ('Wins', 'Date', 'Recorded by', 'Squad')
    for entry in history:
        if entry['player'] == player:
            message += "%-6s %-9s %-20s %s\n" % (entry['wins'], entry['date'], entry['user'], ', '.join(entry['squad']))
    message += '```'
    await client.send_message(context.message.channel, message)


@client.command(name='plot',
                description="Generates a graph of the win history",
                brief="Graph wins",
                pass_context=True)
async def cmd_history(context, *players):
    client.loop.create_task(plot_wins(context, players))


@client.event
async def on_ready():
    await client.change_presence(game=Game(name="Apex Legends"))
    print("Logged in as " + client.user.name)


if __name__ == '__main__':
    TOKEN = os.getenv('TOKEN', sys.argv[1])  # Get at discordapp.com/developers/applications/me
    start_bot(TOKEN)
