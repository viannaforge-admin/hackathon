from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin

import httpx

LOGGER = logging.getLogger(__name__)


@dataclass
class GraphClient:
    base_url: str
    timeout_seconds: float = 15.0
    max_retries: int = 4

    async def list_users(self) -> list[dict[str, Any]]:
        return await self._fetch_all("/v1.0/users")

    async def list_user_chats(self, user_id: str) -> list[dict[str, Any]]:
        return await self._fetch_all(f"/v1.0/users/{user_id}/chats")

    async def list_chat_messages_since(self, chat_id: str, cutoff_iso: str) -> list[dict[str, Any]]:
        safe_cutoff = quote(cutoff_iso, safe=":-+TZ")
        endpoint = f"/v1.0/chats/{chat_id}/messages?$filter=lastModifiedDateTime%20ge%20{safe_cutoff}"
        return await self._fetch_all(endpoint)

    async def _fetch_all(self, endpoint_or_url: str) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        next_url: str | None = endpoint_or_url

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while next_url:
                payload = await self._get_json_with_retry(client, next_url)
                value = payload.get("value", [])
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            collected.append(item)

                raw_next = payload.get("@odata.nextLink")
                if isinstance(raw_next, str) and raw_next.strip():
                    next_url = raw_next if raw_next.startswith("http") else urljoin(self.base_url, raw_next)
                else:
                    next_url = None

        return collected

    async def _get_json_with_retry(self, client: httpx.AsyncClient, endpoint_or_url: str) -> dict[str, Any]:
        url = endpoint_or_url if endpoint_or_url.startswith("http") else urljoin(self.base_url, endpoint_or_url)

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(url)
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise httpx.HTTPStatusError(
                        f"Retryable status code {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    return data
                return {"value": []}
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                delay = min(0.5 * (2**attempt), 4.0)
                LOGGER.warning("Graph request failed (%s). Retrying in %.1fs", exc, delay)
                await asyncio.sleep(delay)

        if last_error is None:
            raise RuntimeError(f"Graph request failed for url={url}")
        raise RuntimeError(f"Graph request failed for url={url}: {last_error}") from last_error
