from __future__ import annotations

from urllib.parse import urlencode


DEFAULT_TOP = 50
DEFAULT_SKIP = 0
MAX_TOP = 500


def validate_pagination(top: int, skip: int) -> None:
    if top < 1:
        raise ValueError("$top must be at least 1")
    if top > MAX_TOP:
        raise ValueError(f"$top must be <= {MAX_TOP}")
    if skip < 0:
        raise ValueError("$skip must be at least 0")


def paginate(items: list[dict], top: int, skip: int) -> tuple[list[dict], int | None]:
    end = skip + top
    page = items[skip:end]
    next_skip = end if end < len(items) else None
    return page, next_skip


def build_next_link(base_path: str, query: dict[str, str], top: int, next_skip: int) -> str:
    next_query = dict(query)
    next_query["$top"] = str(top)
    next_query["$skip"] = str(next_skip)
    return f"{base_path}?{urlencode(next_query)}"
