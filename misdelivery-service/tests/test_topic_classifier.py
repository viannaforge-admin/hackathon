from app.topic_classifier import classify_topic


def test_finance_topic_detected() -> None:
    topic = classify_topic("Please review invoice and payment status", [])
    assert topic == "finance"


def test_normal_when_low_score() -> None:
    topic = classify_topic("Can we sync later", ["notes.txt"])
    assert topic == "normal"


def test_mixed_signals_not_normal() -> None:
    topic = classify_topic("Please review payroll and invoice before release", [])
    assert topic in {"hr_compensation", "finance", "technical"}
