from __future__ import annotations

import json

from app.explanations import build_fallback_explanation
from app.llm_explainer import build_llm_payload


def test_fallback_explanation() -> None:
    explanation, user_prompt = build_fallback_explanation(
        ["name_confusion_possible", "sensitive_topic_with_attachment"]
    )

    assert "Possible autocomplete mistake" in explanation
    assert "Sensitive topic + attachment increases risk." in explanation
    assert explanation.endswith("Please confirm recipients before sending.")
    assert "confirm recipients" in user_prompt.lower()


def test_llm_payload_redaction() -> None:
    payload = build_llm_payload(
        decision="WARN",
        score=72,
        topic="hr_compensation",
        reasons=["name_confusion_possible"],
        signals={
            "sensitive_topic": True,
            "has_attachment": True,
            "attachment_kind": "xlsx",
            "has_external_recipient": False,
            "after_hours": False,
            "unexpected_recipients_count": 1,
            "messageText": "secret payroll details",
        },
        confusion_candidates=[
            {
                "selectedRecipientName": "Rahul Verma",
                "selectedRecipientEmailDomain": "company.com",
                "similarKnownRecipientName": "Rahul Sharma",
                "similarity": 0.93,
            }
        ],
    )

    serialized = json.dumps(payload)
    assert "messageText" not in payload
    assert "secret payroll details" not in serialized
