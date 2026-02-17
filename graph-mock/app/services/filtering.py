from __future__ import annotations

import re
from datetime import datetime

FILTER_RE = re.compile(r"^lastModifiedDateTime\s+ge\s+(.+)$")


def parse_iso8601(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def apply_message_filter(messages: list[dict], filter_expr: str | None) -> list[dict]:
    if not filter_expr:
        return messages

    match = FILTER_RE.match(filter_expr.strip())
    if not match:
        raise ValueError("Only $filter=lastModifiedDateTime ge <ISO8601> is supported")

    threshold = parse_iso8601(match.group(1))
    filtered: list[dict] = []
    for message in messages:
        ts = parse_iso8601(str(message["lastModifiedDateTime"]))
        if ts >= threshold:
            filtered.append(message)
    return filtered
