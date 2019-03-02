#!/usr/bin/env python3 -u
import MySQLdb as SQL

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
        self.host = host;
        self.user = user;
        self.password = password;
        self.database = database;
        self.db = SQL.connect(host, user, password, database)
        self.curs = self.db.cursor()

    def refresh(self):
        self.db = SQL.connect(self.host, self.user, self.password, self.database)

    def save(self):
        self.db.commit()

    def revert(self):
        self.db.rollback()

    def put(self, date, player, wins, *squad):
        def quote(text):
            return f", '{text}'"
        squad = sorted(squad)
        q = (f"INSERT INTO wins (date, player, wins"
             f"{', squad1' if len(squad) > 0 else ''}"
             f"{', squad2' if len(squad) > 1 else ''}"
             f"{', squad3' if len(squad) > 2 else ''}"
             f") "
             f"values('{date}', '{player}', {wins}"
             f"{quote(squad[0]) if len(squad) > 0 else ''}"
             f"{quote(squad[1]) if len(squad) > 1 else ''}"
             f"{quote(squad[2]) if len(squad) > 2 else ''})")
        print(q)
        self.curs.execute(q)

    def get(self, *fields):
        self.refresh()
        self.curs.execute(f"SELECT {', '.join(fields)} FROM wins")
        return self.curs.fetchall()

    def query(self, query):
        print(query)
        self.refresh()
        self.curs.execute(query)
        return self.curs.fetchall()

    def plot(self, player):
        self.refresh()
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
