import sqlite3
from pathlib import Path

# project root is two levels up from backend/config/
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "mobility.db"
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"
INDEXES_FILE = BASE_DIR / "database" / "indexes.sql"


def get_connection():
    """Open a write-capable connection for schema setup and ETL jobs."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-100000")

    return conn


def get_read_connection():
    """Open an immutable, read-only connection for API requests."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    database_uri = DB_PATH.resolve().as_uri() + "?mode=ro&immutable=1"
    conn = sqlite3.connect(
        database_uri,
        uri=True,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -100000")
    return conn


def init_db():
    """Create all tables from schema.sql, then add indexes."""
    conn = get_connection()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA_FILE.read_text())
    conn.executescript(INDEXES_FILE.read_text())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
