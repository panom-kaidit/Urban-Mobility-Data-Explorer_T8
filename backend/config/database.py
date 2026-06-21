import sqlite3
from pathlib import Path

# project root is two levels up from backend/config/
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "mobility.db"
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"
INDEXES_FILE = BASE_DIR / "database" / "indexes.sql"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    # Performance tuning
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-100000")

    return conn




def init_db():
    """Create all tables from schema.sql, then add indexes."""
    conn = get_connection()
    conn.executescript(SCHEMA_FILE.read_text())
    conn.executescript(INDEXES_FILE.read_text())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
