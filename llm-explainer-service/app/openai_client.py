from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a security assistant. You MUST only use the fields provided in the JSON. "
    "Do not invent facts. If unsure, say 'I don't have enough information'."
)
KEYWORD_SYSTEM_PROMPT = (
    "You extract keyword and phrase frequencies from message arrays. "
    "Return only strict JSON. Use lowercase terms and integer counts. "
    "Do not include commentary."
)


@dataclass
class OpenAIConfig:
    api_key: str
    model: str
    temperature: float
    timeout_seconds: float
    keyword_timeout_seconds: float


class OpenAIExplainerClient:
    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config

    async def explain(self, payload: dict[str, Any]) -> dict[str, str] | None:
        prompt = (
            "Return strict JSON with keys explanation and user_prompt. "
            "Keep explanation to max 2-3 sentences and user_prompt one line.\n"
            f"INPUT_JSON:\n{json.dumps(payload, ensure_ascii=True)}"
        )

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        raw = await self._chat(
            prompt=prompt,
            headers=headers,
            timeout_seconds=self.config.timeout_seconds,
            system_prompt=SYSTEM_PROMPT,
        )
        if raw is None:
            return None

        parsed = _extract_json_output(raw)
        if parsed is None:
            return None

        explanation = str(parsed.get("explanation", "")).strip()
        user_prompt = str(parsed.get("user_prompt", "")).strip()
        if not explanation:
            return None
        return {"explanation": explanation, "user_prompt": user_prompt}

    async def extract_keywords(self, messages: list[str]) -> dict[str, dict[str, dict[str, int]]] | None:
        prompt = (
            "Extract important keywords and multi-word phrases from these messages grouped by topic. "
            "Allowed topics: hr_compensation, finance, legal, customer_data, credentials_secrets, technical, normal. "
            "Return strict JSON with shape: "
            "{\"topics\":{\"<topic>\":{\"keywords\":{\"term\":count},\"phrases\":{\"term\":count}}}}. "
            "Use lowercase, no extra keys, and counts must be positive integers.\n"
            f"MESSAGES_JSON:\n{json.dumps(messages, ensure_ascii=True)}"
        )
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        raw = await self._chat(
            prompt=prompt,
            headers=headers,
            timeout_seconds=self.config.keyword_timeout_seconds,
            system_prompt=KEYWORD_SYSTEM_PROMPT,
        )
        if raw is None:
            return None
        parsed = _extract_json_output(raw)
        if parsed is None:
            return None

        topics = parsed.get("topics", {})
        if not isinstance(topics, dict):
            # Backward-compatible fallback if model returns flat shape:
            # {"keywords": {...}, "phrases": {...}}
            topics = {
                "normal": {
                    "keywords": parsed.get("keywords", {}),
                    "phrases": parsed.get("phrases", {}),
                }
            }
        normalized: dict[str, dict[str, dict[str, int]]] = {}
        for topic, payload in topics.items():
            if not isinstance(topic, str) or not isinstance(payload, dict):
                continue
            normalized[topic] = {
                "keywords": _normalize_map(payload.get("keywords", {})),
                "phrases": _normalize_map(payload.get("phrases", {})),
            }
        if not normalized:
            return None
        return {"topics": normalized}

    async def _chat(
        self,
        prompt: str,
        headers: dict[str, str],
        timeout_seconds: float,
        system_prompt: str,
    ) -> dict[str, Any] | None:
        request_body = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=request_body)
                response.raise_for_status()
                LOGGER.info(response.json())
                return response.json()
        except Exception as exc:
            LOGGER.warning("OpenAI call failed (%s): %r", type(exc).__name__, exc)
            return None


def _extract_json_output(raw_response: dict[str, Any]) -> dict[str, Any] | None:
    choices = raw_response.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return None

    first = choices[0]
    if not isinstance(first, dict):
        return None

    message = first.get("message", {})
    if not isinstance(message, dict):
        return None

    content = message.get("content", "")
    if not isinstance(content, str) or not content.strip():
        return None

    try:
        parsed = json.loads(content)
    except Exception:
        return None

    return parsed if isinstance(parsed, dict) else None


def _normalize_map(value: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    if isinstance(value, dict):
        items = value.items()
        for key, count in items:
            term = str(key).strip().lower()
            if not term:
                continue
            try:
                c = int(count)
            except Exception:
                c = 0
            if c > 0:
                result[term] = result.get(term, 0) + c
        return result
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                term = item.strip().lower()
                if term:
                    result[term] = result.get(term, 0) + 1
            elif isinstance(item, dict):
                term = str(item.get("term", "")).strip().lower()
                if not term:
                    continue
                try:
                    c = int(item.get("count", 1))
                except Exception:
                    c = 1
                if c > 0:
                    result[term] = result.get(term, 0) + c
    return result
