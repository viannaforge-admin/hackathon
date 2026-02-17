from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)


@dataclass
class KeywordMinerConfig:
    enabled: bool
    service_url: str
    timeout_seconds: float = 3.0
    max_retries: int = 3


class KeywordMinerClient:
    def __init__(self, config: KeywordMinerConfig) -> None:
        self.config = config

    async def extract(self, messages: list[str]) -> dict[str, dict[str, dict[str, int]]]:
        if not self.config.enabled or not messages:
            return {"topics": {}}

        endpoint = f"{self.config.service_url.rstrip('/')}/v1/keywords/extract"
        payload = {"messages": messages}

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                    response = await client.post(endpoint, json=payload)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        raise httpx.HTTPStatusError(
                            f"Retryable status {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    response.raise_for_status()
                    raw = response.json()
                    return _parse_counts(raw)
            except Exception as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                await asyncio.sleep(min(0.5 * (2**attempt), 2.0))

        LOGGER.warning("Keyword mining failed: %s", last_error)
        return {"topics": {}}


def _parse_counts(raw: Any) -> dict[str, dict[str, dict[str, int]]]:
    if not isinstance(raw, dict):
        return {"topics": {}}

    topics_raw = raw.get("topics", {})
    if not isinstance(topics_raw, dict):
        return {"topics": {}}
    topics: dict[str, dict[str, dict[str, int]]] = {}
    for topic, payload in topics_raw.items():
        if not isinstance(topic, str) or not isinstance(payload, dict):
            continue
        topics[topic] = {
            "keywords": _normalize_map(payload.get("keywords", {})),
            "phrases": _normalize_map(payload.get("phrases", {})),
        }
    return {"topics": topics}


def _normalize_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        term = str(key).strip().lower()
        if not term:
            continue
        try:
            c = int(count)
        except Exception:
            c = 0
        if c > 0:
            result[term] = result.get(term, 0) + c
    return result
