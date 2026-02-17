from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import pstdev
from typing import Any

from app.graph_client import GraphClient
from app.keyword_miner import KeywordMinerClient
from app.topic_classifier import classify_topic

NOW_FIXED = datetime(2026, 2, 15, 0, 0, 0, tzinfo=UTC)
COMPANY_DOMAIN = "company.com"
LOGGER = logging.getLogger(__name__)


@dataclass
class BuildStatus:
    state: str = "idle"
    users_processed: int = 0
    messages_processed: int = 0
    error: str | None = None


@dataclass
class SenderAccumulator:
    known_participants: set[str] = field(default_factory=set)
    known_external_domains: set[str] = field(default_factory=set)
    hour_histogram: Counter[int] = field(default_factory=Counter)
    weekend_messages: int = 0
    message_count: int = 0
    recipient_counts: list[int] = field(default_factory=list)
    attachment_messages: int = 0
    attachment_types: Counter[str] = field(default_factory=Counter)
    topic_histogram: Counter[str] = field(default_factory=Counter)
    topic_recipient_counts: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    topic_external_domain_counts: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))


class BaselineBuilder:
    def __init__(
        self,
        graph_client: GraphClient,
        output_path: Path,
        status: BuildStatus,
        keyword_miner: KeywordMinerClient | None = None,
        keyword_stats_path: Path | None = None,
        keyword_batch_size: int = 200,
    ) -> None:
        self.graph_client = graph_client
        self.output_path = output_path
        self.status = status
        self.keyword_miner = keyword_miner
        self.keyword_stats_path = keyword_stats_path or output_path.with_name("keyword_stats.json")
        self.keyword_batch_size = max(keyword_batch_size, 10)
        self._keyword_buffer: list[str] = []
        self._topic_term_stats: dict[str, dict[str, dict[str, dict[str, int | bool]]]] = self._load_existing_keyword_stats()

    async def build(self, days: int = 35) -> dict[str, Any]:
        cutoff = NOW_FIXED - timedelta(days=days)
        cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
        LOGGER.info("Starting baseline build with cutoff=%s", cutoff_iso)

        self.status.state = "running"
        self.status.users_processed = 0
        self.status.messages_processed = 0
        self.status.error = None

        users = await self.graph_client.list_users()
        users_by_id = {user.get("id"): user for user in users if isinstance(user, dict) and isinstance(user.get("id"), str)}

        senders: dict[str, SenderAccumulator] = {user_id: SenderAccumulator() for user_id in users_by_id}
        processed_message_ids: set[str] = set()

        for user_id in users_by_id:
            chats = await self.graph_client.list_user_chats(user_id)
            self.status.users_processed += 1
            LOGGER.info("Processing user %s (%d chats)", user_id, len(chats))

            for chat in chats:
                if not isinstance(chat, dict):
                    continue
                chat_id = chat.get("id")
                members = chat.get("members", [])
                if not isinstance(chat_id, str) or not isinstance(members, list):
                    continue

                member_ids = [m.get("userId") for m in members if isinstance(m, dict) and isinstance(m.get("userId"), str)]
                if not member_ids:
                    continue

                messages = await self.graph_client.list_chat_messages_since(chat_id, cutoff_iso)
                for message in messages:
                    try:
                        mining_text = self._process_message(message, member_ids, users_by_id, senders, processed_message_ids)
                        if mining_text:
                            await self._enqueue_for_keyword_mining(mining_text)
                    except Exception as exc:
                        LOGGER.warning("Skipping malformed message in chat %s: %s", chat_id, exc)
                        continue

        await self._flush_keyword_buffer()
        baseline = self._finalize(users_by_id, senders, days)
        self.output_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        self._write_keyword_stats(days)
        self.status.state = "completed"
        LOGGER.info(
            "Completed baseline build: users=%d messages=%d",
            self.status.users_processed,
            self.status.messages_processed,
        )
        return baseline

    def _process_message(
        self,
        message: dict[str, Any],
        member_ids: list[str],
        users_by_id: dict[str, dict[str, Any]],
        senders: dict[str, SenderAccumulator],
        processed_message_ids: set[str],
    ) -> str | None:
        message_id = message.get("id")
        if not isinstance(message_id, str):
            raise ValueError("Missing message id")
        if message_id in processed_message_ids:
            return None

        from_user = message.get("from", {}).get("user", {})
        sender_id = from_user.get("id")
        if not isinstance(sender_id, str) or sender_id not in senders:
            raise ValueError("Unknown sender")

        created = _parse_iso(message.get("createdDateTime"))
        attachments = message.get("attachments", [])
        if not isinstance(attachments, list):
            attachments = []
        body_content = str(message.get("body", {}).get("content", ""))

        recipients = [uid for uid in member_ids if uid != sender_id and uid in users_by_id]
        recipient_count = len(recipients)

        accumulator = senders[sender_id]
        accumulator.message_count += 1
        self.status.messages_processed += 1

        accumulator.hour_histogram[created.hour] += 1
        if created.weekday() >= 5:
            accumulator.weekend_messages += 1
        accumulator.recipient_counts.append(recipient_count)

        attachment_kind = _detect_attachment_kind(attachments)
        accumulator.attachment_types[attachment_kind] += 1
        if attachments:
            accumulator.attachment_messages += 1

        attachment_names = [str(item.get("name", "")) for item in attachments if isinstance(item, dict)]
        topic = classify_topic(body_content, attachment_names)
        accumulator.topic_histogram[topic] += 1

        for recipient in recipients:
            accumulator.known_participants.add(recipient)
            accumulator.topic_recipient_counts[topic][recipient] += 1

            external_domain = _extract_external_domain(users_by_id[recipient])
            if external_domain:
                accumulator.known_external_domains.add(external_domain)
                accumulator.topic_external_domain_counts[topic][external_domain] += 1

        processed_message_ids.add(message_id)
        if body_content or attachment_names:
            return f"{body_content} {' '.join(attachment_names)}".strip()
        return None

    async def _enqueue_for_keyword_mining(self, text: str) -> None:
        if self.keyword_miner is None:
            return
        cleaned = text.strip()
        if not cleaned:
            return
        self._keyword_buffer.append(cleaned)
        if len(self._keyword_buffer) >= self.keyword_batch_size:
            await self._flush_keyword_buffer()

    async def _flush_keyword_buffer(self) -> None:
        if self.keyword_miner is None or not self._keyword_buffer:
            return
        batch = list(self._keyword_buffer)
        self._keyword_buffer.clear()
        result = await self.keyword_miner.extract(batch)
        for topic, payload in result.get("topics", {}).items():
            keywords = payload.get("keywords", {})
            phrases = payload.get("phrases", {})
            if isinstance(keywords, dict):
                for term, count in keywords.items():
                    self._increment_term(topic, "keywords", str(term), int(count))
            if isinstance(phrases, dict):
                for term, count in phrases.items():
                    self._increment_term(topic, "phrases", str(term), int(count))

    def _finalize(
        self,
        users_by_id: dict[str, dict[str, Any]],
        senders: dict[str, SenderAccumulator],
        days: int,
    ) -> dict[str, Any]:
        users_payload: dict[str, dict[str, Any]] = {}

        for sender_id, stats in senders.items():
            total = stats.message_count
            recipient_mean = _safe_mean(stats.recipient_counts)
            recipient_std = float(pstdev(stats.recipient_counts)) if len(stats.recipient_counts) > 1 else 0.0

            hour_hist = {str(hour): stats.hour_histogram.get(hour, 0) for hour in range(24)}
            attachment_types = {
                key: stats.attachment_types.get(key, 0)
                for key in ["none", "link", "zip", "xlsx", "pdf", "other"]
            }
            topic_hist = dict(stats.topic_histogram)

            rare_topics: list[str] = []
            if total > 0:
                for topic, count in stats.topic_histogram.items():
                    if topic != "normal" and (count / total) < 0.02:
                        rare_topics.append(topic)

            users_payload[sender_id] = {
                "known_participants": sorted(stats.known_participants),
                "known_external_domains": sorted(stats.known_external_domains),
                "hour_histogram": hour_hist,
                "weekend_rate": _round(stats.weekend_messages / total if total else 0.0),
                "recipient_mean": _round(recipient_mean),
                "recipient_std": _round(recipient_std),
                "attachment_rate": _round(stats.attachment_messages / total if total else 0.0),
                "attachment_types": attachment_types,
                "topic_histogram": topic_hist,
                "rare_topics": sorted(rare_topics),
                "topic_recipient_counts": {
                    topic: dict(counter)
                    for topic, counter in sorted(stats.topic_recipient_counts.items(), key=lambda item: item[0])
                },
                "topic_external_domain_counts": {
                    topic: dict(counter)
                    for topic, counter in sorted(stats.topic_external_domain_counts.items(), key=lambda item: item[0])
                },
            }

        return {
            "meta": {
                "base_url": self.graph_client.base_url,
                "days": days,
                "now_fixed": NOW_FIXED.isoformat().replace("+00:00", "Z"),
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "user_count": len(users_by_id),
                "message_count": self.status.messages_processed,
            },
            "users": users_payload,
        }

    def _write_keyword_stats(self, days: int) -> None:
        sorted_topics: dict[str, dict[str, dict[str, dict[str, int | bool]]]] = {}
        for topic, payload in sorted(self._topic_term_stats.items(), key=lambda item: item[0]):
            sorted_topics[topic] = {
                "keywords": {
                    term: payload["keywords"][term]
                    for term in sorted(payload.get("keywords", {}), key=lambda t: (-int(payload["keywords"][t]["occurrences"]), t))
                },
                "phrases": {
                    term: payload["phrases"][term]
                    for term in sorted(payload.get("phrases", {}), key=lambda t: (-int(payload["phrases"][t]["occurrences"]), t))
                },
            }

        payload = {
            "meta": {
                "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "days": days,
                "message_count": self.status.messages_processed,
                "batch_size": self.keyword_batch_size,
            },
            "topics": sorted_topics,
        }
        self.keyword_stats_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_existing_keyword_stats(self) -> dict[str, dict[str, dict[str, dict[str, int | bool]]]]:
        if not self.keyword_stats_path.exists():
            return {}
        try:
            raw = json.loads(self.keyword_stats_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        topics = raw.get("topics", {})
        if not isinstance(topics, dict):
            return {}
        parsed: dict[str, dict[str, dict[str, dict[str, int | bool]]]] = {}
        for topic, payload in topics.items():
            if not isinstance(topic, str) or not isinstance(payload, dict):
                continue
            keywords_raw = payload.get("keywords", {})
            phrases_raw = payload.get("phrases", {})
            parsed[topic] = {
                "keywords": _parse_term_map(keywords_raw),
                "phrases": _parse_term_map(phrases_raw),
            }
        return parsed

    def _increment_term(self, topic: str, term_type: str, term: str, delta: int) -> None:
        cleaned_topic = topic.strip().lower()
        cleaned_term = term.strip().lower()
        if not cleaned_topic or not cleaned_term or delta <= 0:
            return
        self._topic_term_stats.setdefault(cleaned_topic, {"keywords": {}, "phrases": {}})
        bucket = self._topic_term_stats[cleaned_topic][term_type]
        if cleaned_term not in bucket:
            bucket[cleaned_term] = {"occurrences": 0, "ignored": False, "reasonForIgnore": 0}
        bucket[cleaned_term]["occurrences"] = int(bucket[cleaned_term]["occurrences"]) + int(delta)


def _safe_mean(values: list[int]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _round(value: float) -> float:
    return round(value, 6)


def _parse_iso(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Invalid datetime")
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _extract_external_domain(user: dict[str, Any]) -> str | None:
    user_type = str(user.get("userType", ""))
    email = str(user.get("mail") or user.get("userPrincipalName") or "")
    domain = email.split("@", 1)[1].lower() if "@" in email else ""
    if user_type == "Guest" or (domain and domain != COMPANY_DOMAIN):
        return domain or "external"
    return None


def _detect_attachment_kind(attachments: list[Any]) -> str:
    if not attachments:
        return "none"

    for item in attachments:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).lower()
        content_type = str(item.get("contentType", "")).lower()
        is_link = bool(item.get("isLink"))

        if is_link or content_type == "text/uri-list":
            return "link"

    for item in attachments:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).lower()
        content_type = str(item.get("contentType", "")).lower()
        if name.endswith((".zip", ".7z", ".rar")) or "zip" in content_type:
            return "zip"

    for item in attachments:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).lower()
        content_type = str(item.get("contentType", "")).lower()
        if name.endswith((".xlsx", ".xls")) or "spreadsheet" in content_type:
            return "xlsx"

    for item in attachments:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).lower()
        content_type = str(item.get("contentType", "")).lower()
        if name.endswith(".pdf") or "pdf" in content_type:
            return "pdf"

    return "other"


def _parse_term_map(raw: Any) -> dict[str, dict[str, int | bool]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, int | bool]] = {}
    for term, meta in raw.items():
        cleaned = str(term).strip().lower()
        if not cleaned or not isinstance(meta, dict):
            continue
        occurrences = int(meta.get("occurrences", 0))
        ignored = bool(meta.get("ignored", False))
        reason = int(meta.get("reasonForIgnore", 0))
        result[cleaned] = {
            "occurrences": max(0, occurrences),
            "ignored": ignored,
            "reasonForIgnore": reason if reason in {0, 1, 2} else 0,
        }
    return result
