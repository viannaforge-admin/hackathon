from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


@dataclass
class UserRecord:
    user_id: str
    display_name: str
    email: str
    domain: str
    user_type: str


class UserDirectory:
    def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._users: dict[str, UserRecord] = {}
        self._lock = threading.Lock()

    async def load(self) -> None:
        await self.reload()

    async def reload(self) -> None:
        users = await self._fetch_users()
        with self._lock:
            self._users = users

    def get(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self._users.get(user_id)

    def count(self) -> int:
        with self._lock:
            return len(self._users)

    def all(self) -> dict[str, UserRecord]:
        with self._lock:
            return dict(self._users)

    async def _fetch_users(self) -> dict[str, UserRecord]:
        if httpx is None:
            raise RuntimeError("httpx is required to load user directory")
        collected: dict[str, UserRecord] = {}
        next_url: str | None = "/v1.0/users"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while next_url:
                payload = await self._get_json_with_retry(client, next_url)
                raw_users = payload.get("value", [])
                if isinstance(raw_users, list):
                    for item in raw_users:
                        if not isinstance(item, dict):
                            continue
                        user_id = item.get("id")
                        if not isinstance(user_id, str):
                            continue

                        email = str(item.get("mail") or item.get("userPrincipalName") or "")
                        domain = email.split("@", 1)[1].lower() if "@" in email else ""
                        collected[user_id] = UserRecord(
                            user_id=user_id,
                            display_name=str(item.get("displayName", "")),
                            email=email,
                            domain=domain,
                            user_type=str(item.get("userType", "Member")),
                        )

                raw_next = payload.get("@odata.nextLink")
                if isinstance(raw_next, str) and raw_next.strip():
                    next_url = raw_next if raw_next.startswith("http") else urljoin(self.base_url, raw_next)
                else:
                    next_url = None

        return collected

    async def _get_json_with_retry(self, client: httpx.AsyncClient, endpoint_or_url: str) -> dict[str, Any]:
        url = endpoint_or_url if endpoint_or_url.startswith("http") else urljoin(self.base_url, endpoint_or_url)
        last_error: Exception | None = None

        for attempt in range(5):
            try:
                response = await client.get(url)
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise httpx.HTTPStatusError(
                        f"Retryable status code {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
                return {"value": []}
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= 4:
                    break
                delay = min(0.4 * (2**attempt), 3.0)
                LOGGER.warning("User directory load failed (%s). Retrying in %.1fs", exc, delay)
                await asyncio.sleep(delay)

        if last_error is None:
            raise RuntimeError(f"Unable to fetch users from {url}")
        raise RuntimeError(f"Unable to fetch users from {url}: {last_error}") from last_error
