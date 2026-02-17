from __future__ import annotations

import json
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from app.topic_classifier import classify_topic


def test_topic_classifier_hr_compensation() -> None:
    text = "Payroll update for salary revision and bonus confirmation"
    topic = classify_topic(text, [])
    assert topic == "hr_compensation"


def test_topic_classifier_phrase_priority() -> None:
    text = "Please share customer list and phone number export"
    topic = classify_topic(text, ["contacts_dump.csv"])
    assert topic == "customer_data"


def test_topic_classifier_normal_when_low_score() -> None:
    text = "Can we sync tomorrow morning?"
    topic = classify_topic(text, ["notes.txt"])
    assert topic == "normal"


def test_topic_classifier_uses_json_rules_override(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(
        json.dumps(
            {
                "normal_threshold": 1,
                "topics": {
                    "custom_topic": {
                        "single_keywords": ["roadmap"],
                        "phrases": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("TOPIC_RULES_FILE", str(rules_file))
    topic = classify_topic("please share roadmap", [])
    assert topic == "custom_topic"
