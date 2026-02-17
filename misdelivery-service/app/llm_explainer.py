from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


@dataclass
class LLMExplainerConfig:
    use_llm: bool
    service_url: str
    timeout_seconds: float = 1.5


class LLMExplainer:
    def __init__(self, config: LLMExplainerConfig) -> None:
        self.config = config

    async def generate_explanation(
        self,
        decision: str,
        score: int,
        topic: str,
        reasons: list[str],
        signals: dict[str, Any],
        confusion_candidates: list[dict[str, Any]],
    ) -> tuple[str, str] | None:
        if not self.config.use_llm:
            return None
        if httpx is None:
            return None

        payload = build_llm_payload(decision, score, topic, reasons, signals, confusion_candidates)
        endpoint = f"{self.config.service_url.rstrip('/')}/v1/explain"

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        if not isinstance(data, dict):
            return None
        explanation = str(data.get("explanation", "")).strip()
        user_prompt = str(data.get("user_prompt", "")).strip()
        if not explanation:
            return None
        return explanation, user_prompt


def build_llm_payload(
    decision: str,
    score: int,
    topic: str,
    reasons: list[str],
    signals: dict[str, Any],
    confusion_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_signals = {
        "sensitive_topic": bool(signals.get("sensitive_topic", False)),
        "has_attachment": bool(signals.get("has_attachment", False)),
        "attachment_kind": str(signals.get("attachment_kind", "none")),
        "has_external_recipient": bool(signals.get("has_external_recipient", False)),
        "after_hours": bool(signals.get("after_hours", False)),
        "unexpected_recipients_count": int(signals.get("unexpected_recipients_count", 0)),
    }

    cleaned_candidates: list[dict[str, Any]] = []
    for item in confusion_candidates:
        cleaned_candidates.append(
            {
                "selectedRecipientName": str(item.get("selectedRecipientName", "")),
                "selectedRecipientEmailDomain": str(item.get("selectedRecipientEmailDomain", "unknown")),
                "similarKnownRecipientName": str(item.get("similarKnownRecipientName", "")),
                "similarity": float(item.get("similarity", 0.0)),
            }
        )

    return {
        "decision": decision,
        "score": score,
        "topic": topic,
        "reasons": reasons,
        "signals": selected_signals,
        "confusion_candidates": cleaned_candidates,
        "recommended_actions": [
            "Confirm the recipient identity",
            "Check autocomplete selection",
            "Remove attachments if not intended",
        ],
    }
