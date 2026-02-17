from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.models.error import graph_error_response
from app.services.pagination import DEFAULT_SKIP, DEFAULT_TOP, build_next_link, paginate, validate_pagination


router = APIRouter()


@router.get("/users")
def list_users(
    request: Request,
    top: int = Query(default=DEFAULT_TOP, alias="$top"),
    skip: int = Query(default=DEFAULT_SKIP, alias="$skip"),
) -> dict:
    try:
        validate_pagination(top, skip)
    except ValueError as exc:
        return graph_error_response(400, "BadRequest", str(exc))

    store = request.app.state.store
    page, next_skip = paginate(store.users, top=top, skip=skip)
    response: dict = {"value": page}

    if next_skip is not None:
        response["@odata.nextLink"] = build_next_link(
            base_path=request.url.path,
            query={k: v for k, v in request.query_params.items() if k not in {"$top", "$skip"}},
            top=top,
            next_skip=next_skip,
        )

    return response
