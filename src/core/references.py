from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
import sqlite3


class ReferenceGenerator:
    """Durable, process-safe reference generator for traceable interactions."""

    def __init__(self, prefix: str = "CFS", db_path: str | None = None) -> None:
        self.prefix = prefix
        self._lock = Lock()
        root = Path(__file__).resolve().parents[2]
        self.db_path = Path(db_path) if db_path else root / "data" / "references.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS reference_sequences (prefix TEXT NOT NULL, category TEXT NOT NULL, year INTEGER NOT NULL, sequence INTEGER NOT NULL, PRIMARY KEY(prefix, category, year))")
            db.commit()

    def next(self, category: str = "ENQ") -> str:
        category = category.strip().upper()[:12] or "ENQ"
        year = datetime.now(timezone.utc).year
        with self._lock, sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT sequence FROM reference_sequences WHERE prefix=? AND category=? AND year=?", (self.prefix, category, year)).fetchone()
            sequence = (int(row[0]) if row else 0) + 1
            db.execute("INSERT INTO reference_sequences(prefix, category, year, sequence) VALUES(?,?,?,?) ON CONFLICT(prefix, category, year) DO UPDATE SET sequence=excluded.sequence", (self.prefix, category, year, sequence))
            db.commit()
        return f"{self.prefix}-{category}-{year}-{sequence:06d}"


reference_generator = ReferenceGenerator()
