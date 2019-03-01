#!/usr/bin/python -u

import bot
import sys

if __name__ == '__main__':
	if len(sys.argv) == 2 and sys.argv[1] == "stop":
		bot.stop_bot()
	elif len(sys.argv) == 3 and sys.argv[1] == "start":
		TOKEN = sys.argv[2]
		bot.start_bot(TOKEN)
	else:
		print("Invalid parameters")
