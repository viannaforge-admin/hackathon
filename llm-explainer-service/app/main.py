from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException

from app.models import ExplainRequest, ExplainResponse, KeywordExtractRequest, KeywordExtractResponse
from app.openai_client import OpenAIConfig, OpenAIExplainerClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0"))
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "1.5"))
OPENAI_KEYWORD_TIMEOUT_SECONDS = float(os.getenv("OPENAI_KEYWORD_TIMEOUT_SECONDS", "6.0"))

app = FastAPI(title="LLM Explainer Service", version="1.0.0")


@app.get("/v1/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "has_api_key": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL,
    }


@app.post("/v1/explain", response_model=ExplainResponse)
async def explain(payload: ExplainRequest) -> ExplainResponse:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    client = OpenAIExplainerClient(
        OpenAIConfig(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            timeout_seconds=OPENAI_TIMEOUT_SECONDS,
            keyword_timeout_seconds=OPENAI_KEYWORD_TIMEOUT_SECONDS,
        )
    )
    result = await client.explain(payload.model_dump())
    if result is None:
        raise HTTPException(status_code=502, detail="LLM explanation failed")

    return ExplainResponse(
        explanation=result["explanation"],
        user_prompt=result["user_prompt"],
    )


@app.post("/v1/keywords/extract", response_model=KeywordExtractResponse)
async def extract_keywords(payload: KeywordExtractRequest) -> KeywordExtractResponse:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    if not payload.messages:
        return KeywordExtractResponse(topics={})

    client = OpenAIExplainerClient(
        OpenAIConfig(
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            timeout_seconds=OPENAI_TIMEOUT_SECONDS,
            keyword_timeout_seconds=OPENAI_KEYWORD_TIMEOUT_SECONDS,
        )
    )
    result = await client.extract_keywords(payload.messages)
    if result is None:
        raise HTTPException(status_code=502, detail="Keyword extraction failed")

    return KeywordExtractResponse(topics=result.get("topics", {}))
