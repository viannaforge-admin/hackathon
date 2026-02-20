from __future__ import annotations

from collections.abc import Iterable
from typing import Any
try:
    import ahocorasick
except ModuleNotFoundError:  # pragma: no cover
    ahocorasick = None  # type: ignore[assignment]

TOPIC_KEYWORDS: dict[str, tuple[list[str], list[str]]] = {
    "hr_compensation": (
        [
            "salary",
            "payroll",
            "bonus",
            "increment",
            "appraisal",
            "compensation",
            "ctc",
            "payslip",
        ],
        ["offer letter"],
    ),
    "finance": (
        [
            "invoice",
            "billing",
            "payment",
            "bank",
            "account",
            "ifsc",
            "gst",
            "tds",
            "tax",
            "refund",
            "quotation",
            "po",
        ],
        ["purchase order"],
    ),
    "legal": (
        ["contract", "agreement", "nda", "msa", "sow", "clause", "confidentiality", "termination"],
        ["legal notice"],
    ),
    "customer_data": (
        ["contacts", "address", "export", "dump", "database", "leads", "pii"],
        ["customer list", "client list", "phone number"],
    ),
    "credentials_secrets": (
        ["password", "secret", "token", "ssh", ".pem", "credentials"],
        ["api key", "private key"],
    ),
    "technical": (
        [
            "deploy",
            "release",
            "incident",
            "oncall",
            "logs",
            "stacktrace",
            "error",
            "api",
            "endpoint",
            "kubernetes",
            "ecs",
            "terraform",
        ],
        [],
    ),
}


SENSITIVE_TOPICS = {"hr_compensation", "finance", "legal", "customer_data", "credentials_secrets"}
PATTERN_META: dict[str, tuple[str, int]] = {}
for _topic, (_singles, _phrases) in TOPIC_KEYWORDS.items():
    for _keyword in _singles:
        PATTERN_META[_keyword] = (_topic, 1)
    for _phrase in _phrases:
        PATTERN_META[_phrase] = (_topic, 2)

MATCHER: Any = None
if ahocorasick is not None:
    automaton: Any = ahocorasick.Automaton()
    for pattern in PATTERN_META:
        automaton.add_word(pattern, pattern)
    automaton.make_automaton()
    MATCHER = automaton


def classify_topic(message_text: str, attachment_names: Iterable[str]) -> str:
    text = f"{message_text} {' '.join(attachment_names)}".lower()
    scores: dict[str, int] = {topic: 0 for topic in TOPIC_KEYWORDS}
    seen_patterns: set[str] = set()

    if MATCHER is not None:
        for _, pattern in MATCHER.iter(text):
            seen_patterns.add(str(pattern))
    else:
        for pattern in PATTERN_META:
            if pattern in text:
                seen_patterns.add(pattern)

    for pattern in seen_patterns:
        topic, weight = PATTERN_META[pattern]
        scores[topic] += weight

    best_topic = max(scores, key=scores.get)
    total_signal = sum(scores.values())
    if scores[best_topic] >= 2:
        return best_topic
    if total_signal >= 2:
        return best_topic
    return "normal"
