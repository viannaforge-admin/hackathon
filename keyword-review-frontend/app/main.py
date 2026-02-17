from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

BASELINE_SERVICE_URL = os.getenv("BASELINE_SERVICE_URL", "http://127.0.0.1:8010")
INDEX_PATH = Path(__file__).resolve().parent / "index.html"

app = FastAPI(title="Keyword Review Frontend", version="1.0.0")


class ReviewItem(BaseModel):
    topic: str
    term: str
    termType: str
    action: str


class ReviewSubmitRequest(BaseModel):
    items: list[ReviewItem] = Field(default_factory=list)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_PATH.read_text(encoding="utf-8")


@app.get("/api/topics")
async def api_topics() -> dict[str, Any]:
    return await _proxy_get("/v1/keywords/topics")


@app.get("/api/suggestions")
async def api_suggestions(topic: str) -> dict[str, Any]:
    return await _proxy_get(f"/v1/keywords/suggestions?topic={topic}")


@app.post("/api/submit")
async def api_submit(payload: ReviewSubmitRequest) -> dict[str, Any]:
    return await _proxy_post("/v1/keywords/review", payload.model_dump())


async def _proxy_get(path: str) -> dict[str, Any]:
    url = f"{BASELINE_SERVICE_URL.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    raw = response.json()
    if not isinstance(raw, dict):
        return {}
    return raw


async def _proxy_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{BASELINE_SERVICE_URL.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    raw = response.json()
    if not isinstance(raw, dict):
        return {}
    return raw
