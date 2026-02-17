from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.attachment_utils import detect_attachment_kind
from app.models import AttachmentInput, ConfusionCandidate, PreSendCheckRequest
from app.name_similarity import SimilarityCandidate, normalized_similarity
from app.topic_classifier import SENSITIVE_TOPICS, classify_topic
from app.user_directory import UserDirectory, UserRecord

COMPANY_DOMAIN = "company.com"
MIN_TOPIC_COUNT = 2
SIMILARITY_THRESHOLD = 0.90
DEFAULT_NOW = datetime(2026, 2, 15, 0, 0, 0, tzinfo=UTC)


@dataclass
class ScoringResult:
    decision: str
    score: int
    topic: str
    reasons: list[str]
    signals: dict[str, Any]
    confusion_candidates: list[ConfusionCandidate]


def evaluate_pre_send(
    payload: PreSendCheckRequest,
    sender_baseline: dict[str, Any] | None,
    user_directory: UserDirectory,
) -> ScoringResult:
    now = _parse_now(payload.now)
    attachments = [_attachment_to_dict(item) for item in payload.attachments]
    attachment_names = [item["name"] for item in attachments]
    topic = classify_topic(payload.messageText, attachment_names)
    has_attachment = len(attachments) > 0
    attachment_kind = detect_attachment_kind(attachments)

    all_recipients = payload.to + payload.cc + payload.bcc
    recipient_records = [_resolve_recipient(recipient.userId, recipient.email, user_directory) for recipient in all_recipients]

    external_domains = sorted({r.domain for r in recipient_records if r.is_external and r.domain})
    has_external_recipient = len(external_domains) > 0

    sender_known = set(_safe_list(sender_baseline, "known_participants")) if sender_baseline else set()
    topic_recipient_counts = _safe_nested(sender_baseline, "topic_recipient_counts") if sender_baseline else {}
    topic_external_counts = _safe_nested(sender_baseline, "topic_external_domain_counts") if sender_baseline else {}
    known_external_domains = set(_safe_list(sender_baseline, "known_external_domains")) if sender_baseline else set()

    unexpected_recipients: list[ResolvedRecipient] = []
    unexpected_by_topic_exists = False

    for record in recipient_records:
        expected_by_sender = record.user_id in sender_known if record.user_id else False
        expected_by_topic = _expected_by_topic(record.user_id, topic, topic_recipient_counts)
        recipient_unexpected = (not expected_by_sender) or (topic != "normal" and not expected_by_topic)
        if recipient_unexpected:
            unexpected_recipients.append(record)
        if topic != "normal" and not expected_by_topic:
            unexpected_by_topic_exists = True

    confusion_candidates = find_confusion_candidates(unexpected_recipients, sender_known, user_directory)
    confusion_detected = len(confusion_candidates) > 0

    total_recipients = len(all_recipients)
    recipient_mean = float(sender_baseline.get("recipient_mean", 0.0)) if sender_baseline else 0.0
    recipient_std = float(sender_baseline.get("recipient_std", 0.0)) if sender_baseline else 0.0
    unusual_recipient_count = False
    if sender_baseline:
        threshold = recipient_mean + (2.0 * recipient_std)
        unusual_recipient_count = total_recipients > threshold if recipient_std > 0 else total_recipients > (recipient_mean + 2.0)

    rare_topics = set(_safe_list(sender_baseline, "rare_topics")) if sender_baseline else set()
    rare_topic_for_sender = topic in rare_topics

    reasons: list[str] = []
    score = 0

    if sender_baseline is None:
        score = max(score, 55)
        reasons.append("no_baseline")

    if confusion_detected:
        score += 55
        reasons.append("name_confusion_possible")

    if topic != "normal" and unexpected_by_topic_exists:
        score += 20
        reasons.append("recipient_unusual_for_topic")

    sensitive_topic = topic in SENSITIVE_TOPICS
    if sensitive_topic and has_attachment:
        score += 20
        reasons.append("sensitive_topic_with_attachment")

    if sensitive_topic and has_external_recipient:
        score += 35
        reasons.append("sensitive_topic_to_external")

    if has_external_recipient and sender_baseline is not None:
        if any(domain not in known_external_domains for domain in external_domains):
            score += 20
            reasons.append("new_external_domain_for_sender")

        if topic != "normal":
            topic_domains = topic_external_counts.get(topic, {}) if isinstance(topic_external_counts, dict) else {}
            if any(int(topic_domains.get(domain, 0)) < MIN_TOPIC_COUNT for domain in external_domains):
                score += 20
                reasons.append("new_external_domain_for_topic")

    after_hours = now.hour < 8 or now.hour > 19
    is_weekend = now.weekday() >= 5

    if after_hours and has_external_recipient:
        score += 10
        reasons.append("after_hours_external")

    if unusual_recipient_count:
        score += 10
        reasons.append("unusual_recipient_count")

    if score >= 85:
        decision = "BLOCK"
    elif score >= 55:
        decision = "WARN"
    else:
        decision = "ALLOW"

    signals = {
        "topic": topic,
        "sensitive_topic": sensitive_topic,
        "has_attachment": has_attachment,
        "attachment_kind": attachment_kind,
        "recipient_counts": {
            "to_count": len(payload.to),
            "cc_count": len(payload.cc),
            "bcc_count": len(payload.bcc),
            "total_recipients": total_recipients,
        },
        "has_external_recipient": has_external_recipient,
        "external_domains": external_domains,
        "after_hours": after_hours,
        "is_weekend": is_weekend,
        "unexpected_recipients_count": len(unexpected_recipients),
        "confusion_detected": confusion_detected,
        "confusion_candidates_count": len(confusion_candidates),
        "unusual_recipient_count": unusual_recipient_count,
        "rare_topic_for_sender": rare_topic_for_sender,
    }

    deduped_reasons = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)

    return ScoringResult(
        decision=decision,
        score=score,
        topic=topic,
        reasons=deduped_reasons,
        signals=signals,
        confusion_candidates=confusion_candidates,
    )


@dataclass
class ResolvedRecipient:
    user_id: str | None
    display_name: str
    domain: str
    user_type: str
    is_external: bool


def _resolve_recipient(user_id: str | None, email: str, user_directory: UserDirectory) -> ResolvedRecipient:
    if user_id:
        record = user_directory.get(user_id)
        if record:
            return ResolvedRecipient(
                user_id=record.user_id,
                display_name=record.display_name,
                domain=record.domain,
                user_type=record.user_type,
                is_external=_is_external(record.domain, record.user_type),
            )

    domain = email.split("@", 1)[1].lower() if "@" in email else ""
    display_name = email.split("@", 1)[0] if "@" in email else email
    return ResolvedRecipient(
        user_id=user_id,
        display_name=display_name,
        domain=domain,
        user_type="Guest" if domain and domain != COMPANY_DOMAIN else "Member",
        is_external=bool(domain and domain != COMPANY_DOMAIN),
    )


def _is_external(domain: str, user_type: str) -> bool:
    return user_type == "Guest" or (domain != "" and domain != COMPANY_DOMAIN)


def _expected_by_topic(recipient_id: str | None, topic: str, topic_recipient_counts: dict[str, Any]) -> bool:
    if recipient_id is None:
        return False
    if not isinstance(topic_recipient_counts, dict):
        return False
    topic_map = topic_recipient_counts.get(topic, {})
    if not isinstance(topic_map, dict):
        return False
    return int(topic_map.get(recipient_id, 0)) >= MIN_TOPIC_COUNT


def _safe_list(sender_baseline: dict[str, Any] | None, key: str) -> list[str]:
    if sender_baseline is None:
        return []
    value = sender_baseline.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _safe_nested(sender_baseline: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if sender_baseline is None:
        return {}
    value = sender_baseline.get(key, {})
    return value if isinstance(value, dict) else {}


def _parse_now(value: str | None) -> datetime:
    if not value:
        return DEFAULT_NOW
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)


def _attachment_to_dict(item: AttachmentInput) -> dict[str, Any]:
    return {
        "name": item.name,
        "contentType": item.contentType,
        "size": item.size,
        "isLink": item.isLink,
    }


def find_confusion_candidates(
    unexpected_recipients: list[ResolvedRecipient],
    sender_known_participants: set[str],
    user_directory: UserDirectory,
) -> list[ConfusionCandidate]:
    known_users = [user_directory.get(user_id) for user_id in sender_known_participants]
    known_records = [record for record in known_users if record is not None]
    candidates: list[ConfusionCandidate] = []

    for selected in unexpected_recipients:
        if not selected.display_name:
            continue

        best: SimilarityCandidate | None = None
        for known in known_records:
            if selected.user_id and known.user_id == selected.user_id:
                continue
            similarity = normalized_similarity(selected.display_name, known.display_name)
            if similarity < SIMILARITY_THRESHOLD:
                continue
            maybe = SimilarityCandidate(
                selected_recipient_id=selected.user_id or "unknown",
                selected_recipient_name=selected.display_name,
                similar_known_recipient_id=known.user_id,
                similar_known_recipient_name=known.display_name,
                similarity=similarity,
            )
            if best is None or maybe.similarity > best.similarity:
                best = maybe

        if best is not None:
            candidates.append(
                ConfusionCandidate(
                    selectedRecipientId=best.selected_recipient_id,
                    selectedRecipientName=best.selected_recipient_name,
                    similarKnownRecipientId=best.similar_known_recipient_id,
                    similarKnownRecipientName=best.similar_known_recipient_name,
                    similarity=best.similarity,
                )
            )

    candidates.sort(key=lambda item: item.similarity, reverse=True)
    return candidates[:3]
