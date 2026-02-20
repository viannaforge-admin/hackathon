from __future__ import annotations

from app.models import AttachmentInput, PreSendCheckRequest, RecipientInput
from app.scoring import evaluate_pre_send
from app.user_directory import UserDirectory, UserRecord


def build_directory() -> UserDirectory:
    directory = UserDirectory(base_url="http://127.0.0.1:8000")
    directory._users = {
        "u001": UserRecord("u001", "Rahul Sharma", "rahul.sharma@company.com", "company.com", "Member"),
        "u002": UserRecord("u002", "Rahul Verma", "rahul.verma@company.com", "company.com", "Member"),
        "u003": UserRecord("u003", "Neha Gupta", "neha.gupta@company.com", "company.com", "Member"),
        "u015": UserRecord("u015", "Rahul", "rahul@vendor.com", "vendor.com", "Guest"),
        "u099": UserRecord("u099", "Rahul Varma", "rahul.varma@company.com", "company.com", "Member"),
    }
    return directory


def test_allow_for_new_internal_without_confusion() -> None:
    directory = build_directory()
    baseline = {
        "known_participants": ["u002", "u003"],
        "known_external_domains": ["vendor.com"],
        "recipient_mean": 2.0,
        "recipient_std": 1.0,
        "rare_topics": [],
        "topic_recipient_counts": {"normal": {"u002": 5}},
        "topic_external_domain_counts": {},
    }
    payload = PreSendCheckRequest(
        senderUserId="u001",
        to=[RecipientInput(userId="u003", email="neha.gupta@company.com")],
        cc=[],
        bcc=[],
        messageText="Can we sync for updates",
        attachments=[],
    )

    result = evaluate_pre_send(payload, baseline, directory)
    assert result.decision == "ALLOW"
    assert result.score < 55


def test_warn_when_baseline_missing() -> None:
    directory = build_directory()
    payload = PreSendCheckRequest(
        senderUserId="u404",
        to=[RecipientInput(userId="u003", email="neha.gupta@company.com")],
        messageText="hello",
        attachments=[],
    )

    result = evaluate_pre_send(payload, None, directory)
    assert result.decision == "ALLOW"
    assert result.score < 55
    assert "no_baseline" in result.reasons


def test_block_when_confusion_sensitive_external() -> None:
    directory = build_directory()
    baseline = {
        "known_participants": ["u002", "u003"],
        "known_external_domains": ["partner.org"],
        "recipient_mean": 1.0,
        "recipient_std": 0.2,
        "rare_topics": ["finance"],
        "topic_recipient_counts": {"finance": {"u002": 4}},
        "topic_external_domain_counts": {"finance": {"partner.org": 5}},
    }
    payload = PreSendCheckRequest(
        senderUserId="u001",
        to=[RecipientInput(userId="u099", email="rahul.varma@company.com")],
        cc=[],
        bcc=[RecipientInput(userId="u015", email="rahul@vendor.com")],
        messageText="Please review invoice and payment details",
        attachments=[
            AttachmentInput(
                name="Payroll_Feb.xlsx",
                contentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                size=12345,
                isLink=False,
            )
        ],
        now="2026-02-15T21:30:00Z",
    )

    result = evaluate_pre_send(payload, baseline, directory)
    assert result.decision == "BLOCK"
    assert result.score >= 85
    assert result.signals["confusion_detected"] is True
    assert len(result.confusion_candidates) >= 1
    assert "name_confusion_possible" in result.reasons
