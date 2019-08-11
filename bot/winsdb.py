#!/usr/bin/env python3 -u
import sqlite3

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
    def __init__(self):
        self.db = sqlite3.connect('wins.db')
        self.curs = self.db.cursor()
        if not self.tableExists('wins'):
            self.newDB()

    def tableExists(self, tableName):
        self.refresh()
        self.curs.execute(f''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{tableName}' ''')
        return self.curs.fetchone()[0]==1

    def newDB(self):
        print("Initializing database")
        self.refresh()
        self.curs.execute("""--begin-sql
CREATE TABLE wins (
    date    DATE,
    player  TEXT,
    wins    INTEGER,
    squad1  TEXT,
    squad2  TEXT,
    squad3  TEXT
);""")
        self.save()

    def refresh(self):
        if self.db:
            self.db.commit()
            self.db.close()
        self.db = sqlite3.connect('wins.db')
        self.curs = self.db.cursor()

    def save(self):
        self.db.commit()

    def revert(self):
        self.db.rollback()

    def close(self):
        self.db.close()

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
        self.refresh()

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
        self.curs.execute(f"""--begin-sql
SELECT p.date, p.player, COALESCE(SUM(a.wins), 0) wins
FROM (
    SELECT date, player FROM (
        SELECT player
        FROM wins
        WHERE player='{player}'
        GROUP BY player
    ) q CROSS JOIN ( SELECT DISTINCT date FROM wins) b 
) p LEFT JOIN wins a
ON p.player = a.player AND p.date = a.date 
GROUP BY p.date, p.player ORDER BY p.date, p.player;""")
        return self.curs.fetchall()
