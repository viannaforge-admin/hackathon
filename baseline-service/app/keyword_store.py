from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg


class KeywordStore:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def init_schema(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS keyword_terms (
                        topic TEXT NOT NULL,
                        term_type TEXT NOT NULL CHECK (term_type IN ('keyword','phrase')),
                        term TEXT NOT NULL,
                        occurrences BIGINT NOT NULL DEFAULT 0,
                        ignored BOOLEAN NOT NULL DEFAULT FALSE,
                        reason_for_ignore SMALLINT NOT NULL DEFAULT 0,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (topic, term_type, term)
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_keyword_terms_topic_ignored ON keyword_terms(topic, ignored);")

    def import_json_if_empty(self, keyword_stats_path: Path) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM keyword_terms;")
                count = int(cur.fetchone()[0])
            if count > 0 or not keyword_stats_path.exists():
                return

        raw = json.loads(keyword_stats_path.read_text(encoding="utf-8"))
        topics = raw.get("topics", {}) if isinstance(raw, dict) else {}
        if not isinstance(topics, dict):
            return

        payload: dict[str, dict[str, dict[str, int | bool]]] = {}
        for topic, topic_data in topics.items():
            if not isinstance(topic, str) or not isinstance(topic_data, dict):
                continue
            payload[topic] = {
                "keywords": _normalize_term_meta(topic_data.get("keywords", {})),
                "phrases": _normalize_term_meta(topic_data.get("phrases", {})),
            }
        self.increment_terms(payload)
        self.apply_existing_ignore_flags(payload)

    def increment_terms(self, topics_payload: dict[str, dict[str, dict[str, int | bool]]]) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for topic, topic_data in topics_payload.items():
                    clean_topic = topic.strip().lower()
                    if not clean_topic or not isinstance(topic_data, dict):
                        continue
                    for raw_type, term_type in (("keywords", "keyword"), ("phrases", "phrase")):
                        term_map = topic_data.get(raw_type, {})
                        if not isinstance(term_map, dict):
                            continue
                        for term, value in term_map.items():
                            clean_term = str(term).strip().lower()
                            if not clean_term:
                                continue
                            if isinstance(value, dict):
                                occurrences = int(value.get("occurrences", 0))
                            else:
                                occurrences = int(value)
                            if occurrences <= 0:
                                continue
                            cur.execute(
                                """
                                INSERT INTO keyword_terms (topic, term_type, term, occurrences, ignored, reason_for_ignore)
                                VALUES (%s, %s, %s, %s, FALSE, 0)
                                ON CONFLICT (topic, term_type, term)
                                DO UPDATE SET
                                  occurrences = keyword_terms.occurrences + EXCLUDED.occurrences,
                                  updated_at = NOW();
                                """,
                                (clean_topic, term_type, clean_term, occurrences),
                            )

    def apply_existing_ignore_flags(self, topics_payload: dict[str, dict[str, dict[str, int | bool]]]) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for topic, topic_data in topics_payload.items():
                    clean_topic = topic.strip().lower()
                    if not clean_topic or not isinstance(topic_data, dict):
                        continue
                    for raw_type, term_type in (("keywords", "keyword"), ("phrases", "phrase")):
                        term_map = topic_data.get(raw_type, {})
                        if not isinstance(term_map, dict):
                            continue
                        for term, value in term_map.items():
                            if not isinstance(value, dict):
                                continue
                            ignored = bool(value.get("ignored", False))
                            reason = int(value.get("reasonForIgnore", 0))
                            if not ignored:
                                continue
                            clean_term = str(term).strip().lower()
                            if not clean_term:
                                continue
                            cur.execute(
                                """
                                UPDATE keyword_terms
                                SET ignored = %s,
                                    reason_for_ignore = %s,
                                    updated_at = NOW()
                                WHERE topic = %s AND term_type = %s AND term = %s;
                                """,
                                (True, reason if reason in (1, 2) else 0, clean_topic, term_type, clean_term),
                            )

    def list_topics(self) -> list[str]:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT topic FROM keyword_terms ORDER BY topic;")
                rows = cur.fetchall()
        return [str(row[0]) for row in rows]

    def list_suggestions(self, topic: str) -> list[dict[str, int | str]]:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT term_type, term, occurrences
                    FROM keyword_terms
                    WHERE topic = %s AND ignored = FALSE
                    ORDER BY occurrences DESC, term ASC;
                    """,
                    (topic.strip().lower(),),
                )
                rows = cur.fetchall()

        return [
            {"type": "keyword" if row[0] == "keyword" else "phrase", "term": str(row[1]), "score": int(row[2])}
            for row in rows
        ]

    def apply_review(self, items: list[dict[str, str]]) -> int:
        updated = 0
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for item in items:
                    topic = str(item.get("topic", "")).strip().lower()
                    term = str(item.get("term", "")).strip().lower()
                    term_type = "keyword" if str(item.get("termType", "keyword")) == "keyword" else "phrase"
                    action = str(item.get("action", "ignore"))
                    if not topic or not term:
                        continue
                    reason = 1 if action == "add" else 2

                    cur.execute(
                        """
                        INSERT INTO keyword_terms (topic, term_type, term, occurrences, ignored, reason_for_ignore)
                        VALUES (%s, %s, %s, 0, TRUE, %s)
                        ON CONFLICT (topic, term_type, term)
                        DO UPDATE SET
                          ignored = TRUE,
                          reason_for_ignore = EXCLUDED.reason_for_ignore,
                          updated_at = NOW();
                        """,
                        (topic, term_type, term, reason),
                    )
                    updated += 1
        return updated

    def export_snapshot(self, days: int, message_count: int, batch_size: int) -> dict[str, Any]:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT topic, term_type, term, occurrences, ignored, reason_for_ignore
                    FROM keyword_terms
                    ORDER BY topic ASC, term_type ASC, occurrences DESC, term ASC;
                    """
                )
                rows = cur.fetchall()

        topics: dict[str, dict[str, dict[str, dict[str, int | bool]]]] = {}
        for topic, term_type, term, occurrences, ignored, reason in rows:
            topics.setdefault(topic, {"keywords": {}, "phrases": {}})
            bucket = "keywords" if term_type == "keyword" else "phrases"
            topics[topic][bucket][term] = {
                "occurrences": int(occurrences),
                "ignored": bool(ignored),
                "reasonForIgnore": int(reason),
            }

        return {
            "meta": {
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "days": days,
                "message_count": message_count,
                "batch_size": batch_size,
            },
            "topics": topics,
        }


def _normalize_term_meta(raw: Any) -> dict[str, dict[str, int | bool]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, int | bool]] = {}
    for term, meta in raw.items():
        clean_term = str(term).strip().lower()
        if not clean_term:
            continue
        if isinstance(meta, dict):
            out[clean_term] = {
                "occurrences": int(meta.get("occurrences", 0)),
                "ignored": bool(meta.get("ignored", False)),
                "reasonForIgnore": int(meta.get("reasonForIgnore", 0)),
            }
        else:
            out[clean_term] = {
                "occurrences": int(meta),
                "ignored": False,
                "reasonForIgnore": 0,
            }
    return out
