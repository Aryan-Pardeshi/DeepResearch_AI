import os
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Cumulative count of research-mode "papers" launched by users. Stored in its own
# file (separate from the LangGraph checkpointer) inside the same /app/data volume
# so a mounted Render Disk (or docker-compose volume) keeps the count alive across
# restarts and deploys.
def _stats_db_path() -> Path:
    base = os.getenv("RESEARCH_DB_PATH", "./data/research_state.db")
    return Path(base).resolve().parent / "site_stats.db"


async def _connect() -> aiosqlite.Connection:
    db_path = _stats_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    # WAL lets a reader and writer proceed without blocking each other, and
    # busy_timeout avoids "database is locked" spikes under rare concurrent writes.
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute(
        "CREATE TABLE IF NOT EXISTS paper_stats("
        "id INTEGER PRIMARY KEY CHECK (id=1), "
        "total INTEGER NOT NULL DEFAULT 0)"
    )
    await db.execute("INSERT OR IGNORE INTO paper_stats(id, total) VALUES(1, 0)")
    await db.commit()
    return db


async def init_stats_db() -> None:
    """Warm the stats database at startup (called from the app lifespan)."""
    db = await _connect()
    await db.close()


async def increment_paper_count() -> int:
    """Increment the cumulative paper count and return the new total."""
    db = await _connect()
    try:
        cursor = await db.execute(
            "UPDATE paper_stats SET total = total + 1 WHERE id = 1 RETURNING total"
        )
        row = await cursor.fetchone()
        await db.commit()
        return row[0] if row else 0
    finally:
        await db.close()


async def get_paper_count() -> int:
    """Return the current cumulative paper count (0 if unavailable)."""
    db = await _connect()
    try:
        cursor = await db.execute("SELECT total FROM paper_stats WHERE id = 1")
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await db.close()
