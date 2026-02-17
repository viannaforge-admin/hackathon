from __future__ import annotations

_REASON_TEXT = {
    "name_confusion_possible": "Possible autocomplete mistake: recipient name is similar to a frequent contact.",
    "sensitive_topic_with_attachment": "Sensitive topic + attachment increases risk.",
    "sensitive_topic_to_external": "Sensitive topic with external recipient.",
    "new_external_domain_for_sender": "Recipient domain is unusual for the sender.",
    "recipient_unusual_for_topic": "Recipient is unusual for this topic based on prior behavior.",
    "new_external_domain_for_topic": "External domain is unusual for this topic.",
    "after_hours_external": "After-hours external sending can increase mistakes.",
    "unusual_recipient_count": "Recipient count is higher than sender's normal pattern.",
    "no_baseline": "No historical baseline was available for this sender.",
}


def build_allow_explanation() -> str:
    return "No strong misdelivery signals detected for this draft."


def build_fallback_explanation(reasons: list[str]) -> tuple[str, str]:
    lines: list[str] = []
    for reason in reasons:
        mapped = _REASON_TEXT.get(reason)
        if mapped and mapped not in lines:
            lines.append(mapped)
        if len(lines) >= 2:
            break

    if not lines:
        lines.append("Potential delivery risk was detected.")

    explanation = " ".join(lines + ["Please confirm recipients before sending."])
    user_prompt = "Please confirm recipients and attachments before sending."
    return explanation, user_prompt
