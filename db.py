"""SQLite connection and transaction helper used by the active records."""

import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime


def _app_dir():
    # Portable app: the database lives next to the .exe (or next to this file when run from source).
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _resource_dir():
    # PyInstaller extracts bundled data files to sys._MEIPASS.
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


DB_PATH = os.path.join(_app_dir(), "db.sqlite")
SCHEMA_PATH = os.path.join(_resource_dir(), "schema.sql")

_conn = None
_depth = 0


def configure(path):
    """Use another database file (e.g. for tests). Must be called before the first query."""
    global DB_PATH, _conn
    if _conn is not None:
        _conn.close()
        _conn = None
    DB_PATH = path


def get_connection():
    global _conn
    if _conn is None:
        # Autocommit mode; transactions are handled explicitly by transaction().
        _conn = sqlite3.connect(DB_PATH, isolation_level=None)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def init_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        get_connection().executescript(f.read())


def execute(sql, params=()):
    return get_connection().execute(sql, params)


@contextmanager
def transaction():
    """Reentrant transaction: only the outermost block commits or rolls back."""
    global _depth
    conn = get_connection()
    if _depth == 0:
        conn.execute("BEGIN")
    _depth += 1
    try:
        yield conn
    except BaseException:
        _depth -= 1
        if _depth == 0:
            conn.execute("ROLLBACK")
        raise
    else:
        _depth -= 1
        if _depth == 0:
            conn.execute("COMMIT")


def new_id():
    return str(uuid.uuid4())


def now_iso():
    """Local time, ISO-8601 with UTC offset."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def parse_iso(value):
    return datetime.fromisoformat(value) if value else None
