from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.models.error import graph_error_response
from app.services.filtering import apply_message_filter
from app.services.pagination import DEFAULT_SKIP, DEFAULT_TOP, build_next_link, paginate, validate_pagination


router = APIRouter()


@router.get("/chats/{chat_id}/messages")
def list_chat_messages(
    request: Request,
    chat_id: str,
    top: int = Query(default=DEFAULT_TOP, alias="$top"),
    skip: int = Query(default=DEFAULT_SKIP, alias="$skip"),
    filter_expr: str | None = Query(default=None, alias="$filter"),
) -> dict:
    try:
        validate_pagination(top, skip)
    except ValueError as exc:
        return graph_error_response(400, "BadRequest", str(exc))

    store = request.app.state.store
    if chat_id not in store.chats_by_id:
        return graph_error_response(404, "ItemNotFound", f"Chat '{chat_id}' was not found")

    messages = store.messages_by_chat.get(chat_id, [])
    try:
        filtered_messages = apply_message_filter(messages, filter_expr)
    except ValueError as exc:
        return graph_error_response(400, "BadRequest", str(exc))

    page, next_skip = paginate(filtered_messages, top=top, skip=skip)
    response: dict = {"value": page}

    if next_skip is not None:
        response["@odata.nextLink"] = build_next_link(
            base_path=request.url.path,
            query={k: v for k, v in request.query_params.items() if k not in {"$top", "$skip"}},
            top=top,
            next_skip=next_skip,
        )

    return response
