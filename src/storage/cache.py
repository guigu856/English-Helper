"""Cache layer: get / put / bump_hit / regenerate on top of SQLite."""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.core.models import TaskRequest, TaskResult


class Cache:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ---- reads ----

    def get(self, req: TaskRequest) -> Optional[TaskResult]:
        row = self.conn.execute(
            "SELECT * FROM queries WHERE cache_key = ?",
            (req.cache_key(),),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_result(row, from_cache=True)

    # ---- writes ----

    def put(self, req: TaskRequest, result_text: str) -> TaskResult:
        """Insert (or update on conflict) a cache entry.

        Idempotent on cache_key: if the row already exists (e.g. a race
        between regenerate and a concurrent miss), we update the result
        text and `updated_at` while preserving `is_starred` and `hit_count`.
        """
        key = req.cache_key()
        self.conn.execute(
            """INSERT INTO queries (cache_key, text, task, target_lang, model, result)
                    VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET
                    result = excluded.result,
                    updated_at = CURRENT_TIMESTAMP""",
            (key, req.text, req.task, req.target_lang, req.model, result_text),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM queries WHERE cache_key = ?", (key,)
        ).fetchone()
        return self._row_to_result(row, from_cache=False)

    def bump_hit(self, cache_key: str) -> None:
        self.conn.execute(
            "UPDATE queries SET hit_count = hit_count + 1, updated_at = CURRENT_TIMESTAMP "
            "WHERE cache_key = ?",
            (cache_key,),
        )
        self.conn.commit()

    def regenerate(self, req: TaskRequest, result_text: str) -> TaskResult:
        """Upsert: overwrite existing result for this key (keeps hit_count)."""
        key = req.cache_key()
        existing = self.conn.execute(
            "SELECT id FROM queries WHERE cache_key = ?", (key,)
        ).fetchone()
        if existing is None:
            return self.put(req, result_text)
        self.conn.execute(
            """UPDATE queries
                  SET text = ?, task = ?, target_lang = ?, model = ?,
                      result = ?, updated_at = CURRENT_TIMESTAMP
                WHERE cache_key = ?""",
            (req.text, req.task, req.target_lang, req.model, result_text, key),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM queries WHERE cache_key = ?", (key,)
        ).fetchone()
        return self._row_to_result(row, from_cache=False)

    # ---- helpers ----

    @staticmethod
    def _row_to_result(row: sqlite3.Row, *, from_cache: bool) -> TaskResult:
        return TaskResult(
            text=row["text"],
            task=row["task"],
            target_lang=row["target_lang"],
            model=row["model"],
            result=row["result"],
            cache_key=row["cache_key"],
            is_starred=bool(row["is_starred"]),
            hit_count=row["hit_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            from_cache=from_cache,
        )
