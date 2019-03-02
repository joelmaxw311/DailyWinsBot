#!/usr/bin/env python3 -u
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
import winsdb

BOT_PREFIX = ("?", "!")

plot_queue = []
winsDB = winsdb.WinsDB('localhost', 'monitor', 'password', 'dailywins')
client = Bot(command_prefix=BOT_PREFIX)


def plot_configuration(max_wins, players, data_path='', plot_type='linespoints'):
    config = f"""# gnuplot script file for wins per day
#!/usr/bin/gnuplot
reset
set terminal png

set xdata time
set timefmt "%Y-%m-%d"
set format x "%m/%d"
set xlabel "Date (month/day)"
set ylabel "Wins"

set xrange [*:*]
set yrange [0:{max_wins + 1}]
set xtics 86400
set ytics 1

set title "Daily Wins"
set key below
set grid

plot """
    plots = []
    i = 0
    print(len(players))
    for player in players:
        plots.append(f'"{data_path}{player}.csv" '
                     f'u 1:2 '
                     f'title "{player}" '
                     f'with {plot_type}')
        i += 1
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
    selection = "player='" + "' OR player='".join(players) + "'"
    max_wins = winsDB.query(f"SELECT MAX(SumWins) FROM (SELECT SUM(wins) as SumWins FROM wins "
                            f"WHERE {selection} GROUP BY player, date) as SumWinsTable;")[0][0]
    print(max_wins)
    pattern = re.compile("^[A-Za-z0-9 ]+$")
    # if pattern.match(player):
    for player in players:
        f = open(data_path + player + '.csv', 'w')
        for date, p, wins in winsDB.plot(player):
            f.write(f"{date}, {wins}\n")
        f.close()
    # write gnuplot configuration to a .gp file
    config = plot_configuration(max_wins, players, data_path, 'linespoints')
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


async def request_plot(context, players):
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


async def record_wins_on_date(context, delta, players, date):
    print(f"Transacting {delta} wins for {', '.join(players)} on {date.month}/{date.day}/{date.year}")
    for player in players:
        winsDB.put(date, player, delta, *sorted(players))
    winsDB.save()
    await client.send_message(context.message.channel, f"Recorded {delta} wins on {date.month}/{date.day}/{date.year} "
                                                       f"for the following players: {', '.join(players)}")


async def record_wins(context, delta, players):
    d = datetime.datetime.today()
    date = winsdb.Date(d.year, d.month, d.day)
    await record_wins_on_date(context, delta, players, date)


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
    # load_all_saved_data()
    if is_status_running():
        print("WARNING: Bot may already be running in another process")
    client.loop.create_task(list_servers())
    client.loop.create_task(check_status())
    client.run(token)


@client.command(name='addwins',
                description="Add wins for a list of players.",
                brief="Add records to the wins database",
                aliases=['add'],
                pass_context=True)
async def cmd_addwins(context, count, *players):
    count = int(count)
    if count > 0:
        await record_wins(context, count, players)
    else:
        await client.send_message(context.message.channel, "Cannot add fewer than 1 win.")


@client.command(name='editwins',
                description="Add or subtract wins for player on a date.",
                brief="Adjust records in the wins database",
                aliases=['edit'],
                pass_context=True)
async def cmd_editwins(context, count, player, date):
    count = int(count)
    if count != 0:
        await record_wins_on_date(context, count, *player, date)
    else:
        await client.send_message(context.message.channel, "Cannot add or remove 0 wins.")


@client.command(name='listwins',
                description="List wins for a list of players.",
                brief="View the wins database",
                aliases=['viewwins', 'showwins', 'list', 'view'],
                pass_context=True)
async def cmd_listwins(context, *players):
    if len(players) == 0:
        players = []
        for player in winsDB.query(f"SELECT DISTINCT player FROM wins;"):
            players.append(player[0])
    print(players)
    message = '```'
    message += "%-20s %-6s\n" % ('Player', 'Wins')
    for player in players:
        data = winsDB.query(f"SELECT SUM(wins) FROM wins "
                            f"WHERE player like '{player}';")
        message += " %-20s %-6s\n" % (player, data[0][0])
    message += '```'
    await client.send_message(context.message.channel, message)


@client.command(name='history',
                description="List wins for a list of players.",
                brief="View the wins database",
                aliases=['winlog'],
                pass_context=True)
async def cmd_history(context, player):
    message = '```History of wins for ' + player + '\n'
    message += f"{'Date':<12} {'Wins':<6} {'Squad':<12}\n"
    data = winsDB.query(f"SELECT date, wins, squad1, squad2, squad3 FROM wins "
                        f"WHERE player='{player}';")
    for date, wins, squad1, squad2, squad3 in data:
        message += f"{str(date):<12} {wins:<6} " \
                   f"{squad1 if squad1 else '':<12} {squad2 if squad2 else '':<12} {squad3 if squad3 else '':<12}\n"
    message += '```'
    await client.send_message(context.message.channel, message)


@client.command(name='plot',
                description="Generates a graph of the win history",
                brief="Graph wins",
                pass_context=True)
async def cmd_plot(context, *players):
    client.loop.create_task(request_plot(context, players))


@client.event
async def on_ready():
    await client.change_presence(game=Game(name="Apex Legends"))
    print("Logged in as " + client.user.name)


if __name__ == '__main__':
    TOKEN = os.getenv('TOKEN', sys.argv[1])  # Get at discordapp.com/developers/applications/me
    start_bot(TOKEN)
