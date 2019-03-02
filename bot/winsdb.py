#!/usr/bin/env python3 -u
import MySQLdb as SQL


def quote(text):
    return f"'{text}'"


class Date:
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def pretty(self):
        return f"{self.month}/{self.day}/{self.year}"


class WinsDB:
    def __init__(self, host, user, password, database):
        self.db = SQL.connect(host, user, password, database)
        self.curs = self.db.cursor()

    def save(self):
        self.db.commit()

    def revert(self):
        self.db.rollback()

    def put(self, date, player, wins, *squad):
        squad = sorted(squad)
        self.curs.execute(f"INSERT INTO wins (date, player, wins, squad1, squad2, squad3) "
                          f"values('{Date.pretty(date)}', '{player}', {wins}, "
                          f"{quote(squad[0]) if len(squad) > 0 else None}, "
                          f"{quote(squad[1]) if len(squad) > 1 else None}, "
                          f"{quote(squad[2]) if len(squad) > 2 else None})")

    def get(self, *fields):
        self.curs.execute(f"SELECT {', '.join(fields)} FROM wins")
        return self.curs.fetchall()

    def query(self, query):
        self.curs.execute(query)
        return self.curs.fetchall()

    def plot(self, player):
        self.curs.execute(f"SELECT p.date, p.player, COALESCE(SUM(a.wins), 0) wins "
                          f"FROM ( "
                          f"    SELECT date, player FROM ( "
                          f"        SELECT player "
                          f"        FROM wins "
                          f"        WHERE player='{player}' "
                          f"        GROUP BY player "
                          f"    ) q CROSS JOIN ( SELECT DISTINCT date FROM wins) b  "
                          f") p LEFT JOIN wins a "
                          f"ON p.player = a.player AND p.date = a.date  "
                          f"GROUP BY date, player ORDER BY date, player;")
        return self.curs.fetchall()
