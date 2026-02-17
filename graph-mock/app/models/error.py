from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.responses import JSONResponse


def graph_error_response(status_code: int, code: str, message: str) -> JSONResponse:
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    request_id = str(uuid4())
    payload = {
        "error": {
            "code": code,
            "message": message,
            "innerError": {
                "date": now,
                "request-id": request_id,
                "client-request-id": request_id,
            },
        }
    }
    return JSONResponse(status_code=status_code, content=payload)
