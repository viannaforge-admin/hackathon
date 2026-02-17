from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
try:
    import ahocorasick
except ModuleNotFoundError:  # pragma: no cover
    ahocorasick = None  # type: ignore[assignment]

DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "config" / "topic_keywords.json"
RULES_PATH_ENV = "TOPIC_RULES_FILE"
_RULES_CACHE: "TopicRules | None" = None
_RULES_MTIME: float | None = None


@dataclass
class TopicRules:
    normal_threshold: int
    topics: dict[str, tuple[list[str], list[str]]]
    matcher: Any
    pattern_meta: dict[str, tuple[str, int]]


def classify_topic(body_content: str, attachment_names: Iterable[str]) -> str:
    rules = _get_topic_rules()
    text = f"{body_content} {' '.join(attachment_names)}".lower()
    scores: dict[str, int] = {topic: 0 for topic in rules.topics}
    seen_patterns: set[str] = set()

    if ahocorasick is not None:
        for _, pattern in rules.matcher.iter(text):
            seen_patterns.add(str(pattern))
    else:
        for pattern in rules.pattern_meta:
            if pattern in text:
                seen_patterns.add(pattern)

    for pattern in seen_patterns:
        topic, weight = rules.pattern_meta[pattern]
        scores[topic] += weight

    best_topic = max(scores, key=scores.get)
    if scores[best_topic] < rules.normal_threshold:
        return "normal"
    return best_topic


def _get_topic_rules() -> TopicRules:
    global _RULES_CACHE, _RULES_MTIME
    path = _resolve_rules_path()
    mtime = path.stat().st_mtime
    if _RULES_CACHE is not None and _RULES_MTIME == mtime:
        return _RULES_CACHE

    raw = json.loads(path.read_text(encoding="utf-8"))
    _RULES_CACHE = _parse_rules(raw)
    _RULES_MTIME = mtime
    return _RULES_CACHE


def _resolve_rules_path() -> Path:
    configured = os.getenv(RULES_PATH_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_RULES_PATH


def _parse_rules(raw: Any) -> TopicRules:
    if not isinstance(raw, dict):
        raise ValueError("Topic rules config must be an object")

    threshold = raw.get("normal_threshold", 2)
    if not isinstance(threshold, int) or threshold < 1:
        raise ValueError("normal_threshold must be an integer >= 1")

    raw_topics = raw.get("topics")
    if not isinstance(raw_topics, dict) or not raw_topics:
        raise ValueError("topics must be a non-empty object")

    topics: dict[str, tuple[list[str], list[str]]] = {}
    pattern_meta: dict[str, tuple[str, int]] = {}
    for topic, topic_value in raw_topics.items():
        if not isinstance(topic, str) or not isinstance(topic_value, dict):
            raise ValueError("Invalid topic rule entry")
        singles = topic_value.get("single_keywords", [])
        phrases = topic_value.get("phrases", [])
        if not isinstance(singles, list) or not isinstance(phrases, list):
            raise ValueError("single_keywords and phrases must be arrays")
        cleaned_singles = [str(item).lower() for item in singles if str(item).strip()]
        cleaned_phrases = [str(item).lower() for item in phrases if str(item).strip()]
        topics[topic] = (cleaned_singles, cleaned_phrases)
        for keyword in cleaned_singles:
            pattern_meta[keyword] = (topic, 1)
        for phrase in cleaned_phrases:
            pattern_meta[phrase] = (topic, 2)
    matcher = _build_matcher(pattern_meta.keys())
    return TopicRules(normal_threshold=threshold, topics=topics, matcher=matcher, pattern_meta=pattern_meta)


def _build_matcher(patterns: Iterable[str]) -> Any:
    if ahocorasick is None:
        return None
    automaton: Any = ahocorasick.Automaton()
    for pattern in patterns:
        automaton.add_word(pattern, pattern)
    automaton.make_automaton()
    return automaton
