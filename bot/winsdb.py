#!/usr/bin/env python -u
import MySQLdb as SQL


class Date:
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day


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
                          f"values('{date.year:04d}-{date.month:02d}-{date.day:02d}', '{player}', {wins}, "
                          f"'{(squad[0] if len(squad) > 0 else None)}', "
                          f"'{(squad[1] if len(squad) > 1 else None)}', "
                          f"'{(squad[2] if len(squad) > 2 else None)}')")

    def get(self, *fields):
        self.curs.execute(f"SELECT {', '.join(fields)} FROM wins")
        return self.curs.fetchall()

    def query(self, query):
        self.curs.execute(query)
        return self.curs.fetchall()
