from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RecipientInput(BaseModel):
    userId: str | None = None
    email: str


class AttachmentInput(BaseModel):
    name: str
    contentType: str
    size: int = 0
    isLink: bool = False


class PreSendCheckRequest(BaseModel):
    senderUserId: str
    to: list[RecipientInput] = Field(default_factory=list)
    cc: list[RecipientInput] = Field(default_factory=list)
    bcc: list[RecipientInput] = Field(default_factory=list)
    messageText: str = ""
    attachments: list[AttachmentInput] = Field(default_factory=list)
    now: str | None = None


class ConfusionCandidate(BaseModel):
    selectedRecipientId: str
    selectedRecipientName: str
    similarKnownRecipientId: str
    similarKnownRecipientName: str
    similarity: float


class PreSendCheckResponse(BaseModel):
    decision: Literal["ALLOW", "WARN", "BLOCK"]
    score: int
    topic: str
    reasons: list[str]
    signals: dict[str, Any]
    explanation: str
    confusion_candidates: list[ConfusionCandidate]
