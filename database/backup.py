import os
import sqlite3
from datetime import datetime


def backup_database(db_path: str, backups_dir: str = "backups") -> str:
    os.makedirs(backups_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backups_dir, f"backup_{timestamp}.db")

    with sqlite3.connect(db_path) as source:
        with sqlite3.connect(backup_path) as target:
            source.backup(target)

    return backup_path
