from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class BaselineStore:
    def __init__(self, baseline_path: Path) -> None:
        self._path = baseline_path
        self._lock = threading.Lock()
        self._payload: dict[str, Any] = {"meta": {}, "users": {}}

    def load(self) -> None:
        self.reload()

    def reload(self) -> None:
        with self._lock:
            if not self._path.exists():
                self._payload = {"meta": {}, "users": {}}
                return
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                self._payload = {"meta": {}, "users": {}}
                return
            users = raw.get("users", {})
            meta = raw.get("meta", {})
            self._payload = {
                "meta": meta if isinstance(meta, dict) else {},
                "users": users if isinstance(users, dict) else {},
            }

    def get_sender_baseline(self, sender_user_id: str) -> dict[str, Any] | None:
        with self._lock:
            users = self._payload.get("users", {})
            if not isinstance(users, dict):
                return None
            baseline = users.get(sender_user_id)
            if isinstance(baseline, dict):
                return baseline
            return None

    def user_count(self) -> int:
        with self._lock:
            users = self._payload.get("users", {})
            return len(users) if isinstance(users, dict) else 0

    def meta(self) -> dict[str, Any]:
        with self._lock:
            meta = self._payload.get("meta", {})
            return dict(meta) if isinstance(meta, dict) else {}
