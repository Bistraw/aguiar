import sqlite3

class UnitOfWork
    db_path = "./db.sqlite"

    def __init__(self):
        self.conn = sqlite3.connect(db_path)
    
    
