from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MessageFromUserModel(BaseModel):
    id: str
    displayName: str


class MessageFromModel(BaseModel):
    user: MessageFromUserModel


class MessageBodyModel(BaseModel):
    contentType: Literal["text"]
    content: str


class MessageAttachmentModel(BaseModel):
    id: str
    name: str
    contentType: str
    size: int
    isLink: bool


class MessageModel(BaseModel):
    id: str
    createdDateTime: str
    lastModifiedDateTime: str
    from_: MessageFromModel = Field(alias="from")
    body: MessageBodyModel
    importance: Literal["normal", "high"]
    attachments: list[MessageAttachmentModel]

    model_config = {"populate_by_name": True}
