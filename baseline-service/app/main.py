from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.baseline_db_store import BaselineDBStore
from app.baseline_builder import BaselineBuilder, BuildStatus
from app.graph_client import GraphClient
from app.keyword_miner import KeywordMinerClient, KeywordMinerConfig
from app.keyword_store import KeywordStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

BASE_URL_DEFAULT = "http://127.0.0.1:8000"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "baseline.json"
KEYWORD_STATS_PATH = Path(__file__).resolve().parents[1] / "keyword_stats.json"
TOPIC_RULES_PATH = Path(__file__).resolve().parent / "config" / "topic_keywords.json"

app = FastAPI(title="Topic-Aware Baseline Builder", version="1.0.0")
app.state.status = BuildStatus()
app.state.task = None
app.state.lock = asyncio.Lock()
app.state.keyword_store = None
app.state.baseline_store = None


class BuildRequest(BaseModel):
    days: int = Field(default=35, ge=1, le=365)


class KeywordReviewItem(BaseModel):
    topic: str
    term: str
    termType: Literal["keyword", "phrase"]
    action: Literal["add", "ignore"]


class KeywordReviewRequest(BaseModel):
    items: list[KeywordReviewItem] = Field(default_factory=list)


@app.post("/v1/baseline/build")
async def build_baseline(request: BuildRequest | None = None) -> dict[str, str]:
    days = request.days if request else 35
    status: BuildStatus = app.state.status

    if status.state == "running":
        return {"status": "started"}

    async def _runner() -> None:
        async with app.state.lock:
            try:
                base_url = os.getenv("GRAPH_BASE_URL", BASE_URL_DEFAULT)
                keyword_miner = KeywordMinerClient(
                    KeywordMinerConfig(
                        enabled=os.getenv("USE_LLM_KEYWORD_MINER", "false").lower() == "true",
                        service_url=os.getenv("KEYWORD_MINER_URL", "http://127.0.0.1:8030"),
                        timeout_seconds=float(os.getenv("KEYWORD_MINER_TIMEOUT_SECONDS", "3.0")),
                        max_retries=int(os.getenv("KEYWORD_MINER_MAX_RETRIES", "3")),
                    )
                )
                builder = BaselineBuilder(
                    GraphClient(base_url=base_url),
                    OUTPUT_PATH,
                    status,
                    keyword_miner=keyword_miner,
                    baseline_store=app.state.baseline_store,
                    keyword_store=app.state.keyword_store,
                    keyword_stats_path=KEYWORD_STATS_PATH,
                    keyword_batch_size=int(os.getenv("KEYWORD_MINER_BATCH_SIZE", "200")),
                    keyword_miner_workers=int(os.getenv("KEYWORD_MINER_WORKERS", "3")),
                )
                await builder.build(days=days)
            except Exception as exc:
                status.state = "failed"
                status.error = str(exc)
                logging.exception("Baseline build failed")

    app.state.task = asyncio.create_task(_runner())
    return {"status": "started"}


@app.get("/v1/baseline/status")
def baseline_status() -> dict[str, int | str]:
    status: BuildStatus = app.state.status
    return {
        "state": status.state,
        "users_processed": status.users_processed,
        "messages_processed": status.messages_processed,
    }


@app.get("/v1/baseline/{user_id}")
def get_user_baseline(user_id: str) -> dict:
    baseline_store: BaselineDBStore | None = app.state.baseline_store
    if baseline_store is not None:
        payload = baseline_store.get_user(user_id)
        if payload is not None:
            return payload

    if not OUTPUT_PATH.exists():
        raise HTTPException(status_code=404, detail="baseline.json not found")

    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    users = payload.get("users", {})
    if user_id not in users:
        raise HTTPException(status_code=404, detail=f"user '{user_id}' baseline not found")
    return users[user_id]


@app.get("/v1/keywords/topics")
def list_keyword_topics() -> dict[str, list[str]]:
    keyword_store: KeywordStore | None = app.state.keyword_store
    if keyword_store is not None:
        return {"topics": keyword_store.list_topics()}
    stats = _read_keyword_stats()
    topics = stats.get("topics", {})
    if not isinstance(topics, dict):
        return {"topics": []}
    return {"topics": sorted([str(topic) for topic in topics.keys()])}


@app.get("/v1/keywords/suggestions")
def list_keyword_suggestions(topic: str) -> dict[str, list[dict[str, int | str]]]:
    keyword_store: KeywordStore | None = app.state.keyword_store
    if keyword_store is not None:
        return {"value": keyword_store.list_suggestions(topic)}
    stats = _read_keyword_stats()
    topics = stats.get("topics", {})
    if not isinstance(topics, dict):
        return {"value": []}
    topic_data = topics.get(topic, {})
    if not isinstance(topic_data, dict):
        return {"value": []}

    rows: list[dict[str, int | str]] = []
    for raw_type in ("keywords", "phrases"):
        items = topic_data.get(raw_type, {})
        if not isinstance(items, dict):
            continue
        for term, meta in items.items():
            if not isinstance(meta, dict):
                continue
            if bool(meta.get("ignored", False)):
                continue
            rows.append(
                {
                    "term": str(term),
                    "type": "keyword" if raw_type == "keywords" else "phrase",
                    "score": int(meta.get("occurrences", 0)),
                }
            )

    rows.sort(key=lambda row: (-int(row["score"]), str(row["term"])))
    return {"value": rows}


@app.post("/v1/keywords/review")
def submit_keyword_review(payload: KeywordReviewRequest) -> dict[str, int]:
    if not payload.items:
        return {"updated": 0}

    keyword_store: KeywordStore | None = app.state.keyword_store
    rules = _read_topic_rules()
    if keyword_store is not None:
        updated = keyword_store.apply_review([item.model_dump() for item in payload.items])
    else:
        stats = _read_keyword_stats()
        topics = stats.setdefault("topics", {})
        if not isinstance(topics, dict):
            raise HTTPException(status_code=500, detail="keyword_stats.json malformed")
        updated = 0
        for item in payload.items:
            topic = item.topic.strip().lower()
            term = item.term.strip().lower()
            if not topic or not term:
                continue
            topic_stats = topics.setdefault(topic, {"keywords": {}, "phrases": {}})
            if not isinstance(topic_stats, dict):
                continue
            bucket_key = "keywords" if item.termType == "keyword" else "phrases"
            bucket = topic_stats.setdefault(bucket_key, {})
            if not isinstance(bucket, dict):
                continue
            entry = bucket.setdefault(term, {"occurrences": 0, "ignored": False, "reasonForIgnore": 0})
            if not isinstance(entry, dict):
                continue
            entry["ignored"] = True
            entry["reasonForIgnore"] = 1 if item.action == "add" else 2
            if "occurrences" not in entry:
                entry["occurrences"] = 0
            updated += 1
        _write_keyword_stats(stats)

    for item in payload.items:
        topic = item.topic.strip().lower()
        term = item.term.strip().lower()
        if item.action == "add" and topic and term:
            _add_term_to_rules(rules, topic, term, item.termType)

    _write_topic_rules(rules)
    return {"updated": updated}


@app.on_event("startup")
async def startup() -> None:
    use_db = os.getenv("KEYWORD_DB_ENABLED", "false").lower() == "true"
    if not use_db:
        app.state.keyword_store = None
        app.state.baseline_store = None
        return
    dsn = os.getenv("KEYWORD_DB_DSN", "postgresql://postgres:postgres@keyword-db:5432/keywords")
    baseline_store = BaselineDBStore(dsn=dsn)
    baseline_store.init_schema()
    app.state.baseline_store = baseline_store
    store = KeywordStore(dsn=dsn)
    store.init_schema()
    store.import_json_if_empty(KEYWORD_STATS_PATH)
    app.state.keyword_store = store


def _read_keyword_stats() -> dict:
    if not KEYWORD_STATS_PATH.exists():
        return {"meta": {}, "topics": {}}
    raw = json.loads(KEYWORD_STATS_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {"meta": {}, "topics": {}}


def _write_keyword_stats(payload: dict) -> None:
    KEYWORD_STATS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_topic_rules() -> dict:
    if not TOPIC_RULES_PATH.exists():
        raise HTTPException(status_code=500, detail="topic keywords config missing")
    raw = json.loads(TOPIC_RULES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="topic keywords config malformed")
    return raw


def _write_topic_rules(payload: dict) -> None:
    TOPIC_RULES_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _add_term_to_rules(rules: dict, topic: str, term: str, term_type: str) -> None:
    topics = rules.setdefault("topics", {})
    if not isinstance(topics, dict):
        return
    topic_entry = topics.setdefault(topic, {"single_keywords": [], "phrases": []})
    if not isinstance(topic_entry, dict):
        return
    list_key = "single_keywords" if term_type == "keyword" else "phrases"
    terms = topic_entry.setdefault(list_key, [])
    if not isinstance(terms, list):
        return
    if term not in [str(item).lower() for item in terms]:
        terms.append(term)
