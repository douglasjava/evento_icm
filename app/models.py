import sqlite3
from flask import g

DATABASE = 'event.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inscritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                igreja TEXT NOT NULL,
                telefone TEXT,
                funcao TEXT,
                qrcode TEXT UNIQUE NOT NULL,
                presente INTEGER DEFAULT 0
            );
        """)
        db.commit()


        app.teardown_appcontext(close_db)