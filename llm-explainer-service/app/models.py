from __future__ import annotations

from pydantic import BaseModel, Field


class SignalsInput(BaseModel):
    sensitive_topic: bool = False
    has_attachment: bool = False
    attachment_kind: str = "none"
    has_external_recipient: bool = False
    after_hours: bool = False
    unexpected_recipients_count: int = 0


class ConfusionCandidateInput(BaseModel):
    selectedRecipientName: str
    selectedRecipientEmailDomain: str
    similarKnownRecipientName: str
    similarity: float


class ExplainRequest(BaseModel):
    decision: str
    score: int
    topic: str
    reasons: list[str] = Field(default_factory=list)
    signals: SignalsInput
    confusion_candidates: list[ConfusionCandidateInput] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class ExplainResponse(BaseModel):
    explanation: str
    user_prompt: str


class KeywordExtractRequest(BaseModel):
    messages: list[str] = Field(default_factory=list)


class KeywordExtractResponse(BaseModel):
    topics: dict[str, dict[str, dict[str, int]]] = Field(default_factory=dict)
