from app.services.pagination import build_next_link, paginate, validate_pagination
from urllib.parse import parse_qs, urlparse


def test_paginate_returns_expected_slice_and_next_skip() -> None:
    items = [{"id": str(i)} for i in range(120)]
    page, next_skip = paginate(items, top=50, skip=25)

    assert len(page) == 50
    assert page[0]["id"] == "25"
    assert page[-1]["id"] == "74"
    assert next_skip == 75


def test_paginate_without_remaining_items() -> None:
    items = [{"id": str(i)} for i in range(60)]
    page, next_skip = paginate(items, top=50, skip=50)

    assert len(page) == 10
    assert next_skip is None


def test_validate_pagination_rejects_invalid_values() -> None:
    for top, skip in [(0, 0), (501, 0), (5, -1)]:
        raised = False
        try:
            validate_pagination(top=top, skip=skip)
        except ValueError:
            raised = True
        assert raised


def test_build_next_link_preserves_extra_query() -> None:
    next_link = build_next_link(
        "/v1.0/chats/c001/messages",
        query={"$filter": "lastModifiedDateTime ge 2026-01-20T00:00:00Z"},
        top=30,
        next_skip=60,
    )

    parsed = urlparse(next_link)
    query = parse_qs(parsed.query)

    assert query["$top"] == ["30"]
    assert query["$skip"] == ["60"]
    assert "$filter" in query
