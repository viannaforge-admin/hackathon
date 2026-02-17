from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatMemberModel(BaseModel):
    userId: str
    displayName: str


class ChatModel(BaseModel):
    id: str
    topic: str | None = None
    chatType: Literal["oneOnOne", "group"]
    members: list[ChatMemberModel]
