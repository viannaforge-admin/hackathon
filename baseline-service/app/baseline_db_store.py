from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Json


class BaselineDBStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def init_schema(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS baseline_meta (
                        id SMALLINT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS baseline_users (
                        user_id TEXT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )

    def save_baseline(self, baseline_payload: dict[str, Any]) -> None:
        users = baseline_payload.get("users", {})
        meta = baseline_payload.get("meta", {})
        if not isinstance(users, dict):
            users = {}
        if not isinstance(meta, dict):
            meta = {}

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM baseline_users;")
                for user_id, payload in users.items():
                    if not isinstance(user_id, str) or not isinstance(payload, dict):
                        continue
                    cur.execute(
                        """
                        INSERT INTO baseline_users (user_id, payload)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id)
                        DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW();
                        """,
                        (user_id, Json(payload)),
                    )

                cur.execute(
                    """
                    INSERT INTO baseline_meta (id, payload)
                    VALUES (1, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW();
                    """,
                    (Json(meta),),
                )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload FROM baseline_users WHERE user_id = %s;", (user_id,))
                row = cur.fetchone()
        if not row:
            return None
        payload = row[0]
        return payload if isinstance(payload, dict) else None

    def count_users(self) -> int:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM baseline_users;")
                row = cur.fetchone()
        return int(row[0]) if row else 0
