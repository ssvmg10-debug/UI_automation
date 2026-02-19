"""
Fragment persistence (SQLite). Stores only action intent, URLs, no selectors.
"""
import sqlite3
import json
import os
from pathlib import Path
from typing import List, Tuple, Any

from .fragment_model import FlowFragment


def _default_db_path() -> str:
    base = Path(__file__).resolve().parent.parent.parent
    return str(base / "flow_fragments.db")


class FragmentStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _default_db_path()
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()

    def _create_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fragments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT,
                start_url TEXT,
                end_url TEXT,
                steps TEXT,
                success_count INTEGER
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fragments_lookup ON fragments(site, start_url)"
        )
        self.conn.commit()

    def save(self, fragment: FlowFragment) -> None:
        self.conn.execute(
            """
            INSERT INTO fragments (site, start_url, end_url, steps, success_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                fragment.site,
                fragment.start_url,
                fragment.end_url,
                json.dumps(fragment.steps),
                fragment.success_count,
            ),
        )
        self.conn.commit()

    def find_existing(
        self, site: str, start_url: str, steps_json: str, end_url: str
    ) -> int | None:
        """Return fragment id if exists, else None."""
        cur = self.conn.execute(
            """
            SELECT id FROM fragments
            WHERE site = ? AND start_url = ? AND steps = ? AND end_url = ?
            """,
            (site, start_url, steps_json, end_url),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def increment_success_count(self, fragment_id: int) -> None:
        self.conn.execute(
            "UPDATE fragments SET success_count = success_count + 1 WHERE id = ?",
            (fragment_id,),
        )
        self.conn.commit()

    def save_or_update(self, fragment: FlowFragment) -> bool:
        """
        Save fragment or increment success_count if exists.
        Returns True if new insert, False if updated.
        """
        steps_json = json.dumps(fragment.steps)
        existing = self.find_existing(
            fragment.site, fragment.start_url, steps_json, fragment.end_url
        )
        if existing:
            self.increment_success_count(existing)
            return False
        self.save(fragment)
        return True

    def fetch_all(self) -> List[Tuple[Any, ...]]:
        cur = self.conn.execute(
            "SELECT id, site, start_url, end_url, steps, success_count FROM fragments"
        )
        return cur.fetchall()

    def close(self) -> None:
        self.conn.close()
