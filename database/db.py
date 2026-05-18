import os
import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    timeout = float(os.getenv("SQLITE_TIMEOUT_SECONDS", "30"))
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)};")

    return conn
