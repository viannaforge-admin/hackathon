from __future__ import annotations

import asyncio

from app.graph_client import GraphClient


def test_graph_client_fetches_all_pages_with_nextlink() -> None:
    client = GraphClient(base_url="http://127.0.0.1:8000")

    responses = {
        "/v1.0/users": {
            "value": [{"id": "u1"}, {"id": "u2"}],
            "@odata.nextLink": "/v1.0/users?$top=2&$skip=2",
        },
        "http://127.0.0.1:8000/v1.0/users?$top=2&$skip=2": {
            "value": [{"id": "u3"}],
        },
    }

    async def fake_get_json_with_retry(_client: object, endpoint_or_url: str) -> dict:
        return responses[endpoint_or_url]

    client._get_json_with_retry = fake_get_json_with_retry  # type: ignore[method-assign]

    result = asyncio.run(client._fetch_all("/v1.0/users"))
    assert [item["id"] for item in result] == ["u1", "u2", "u3"]
