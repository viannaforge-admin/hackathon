from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI

from app.baseline_store import BaselineStore
from app.explanations import build_allow_explanation, build_fallback_explanation
from app.llm_explainer import LLMExplainer, LLMExplainerConfig
from app.models import PreSendCheckRequest, PreSendCheckResponse
from app.scoring import evaluate_pre_send
from app.user_directory import UserDirectory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger(__name__)

GRAPH_BASE_URL = os.getenv("GRAPH_BASE_URL", "http://127.0.0.1:8000")
BASELINE_PATH = Path(os.getenv("BASELINE_PATH", "./baseline.json")).resolve()
USE_LLM_EXPLAINER = os.getenv("USE_LLM_EXPLAINER", "false").lower() == "true"
LLM_EXPLAINER_URL = os.getenv("LLM_EXPLAINER_URL", "http://127.0.0.1:8030")

app = FastAPI(title="Misdelivery Detection Service", version="1.0.0")
app.state.baseline_store = BaselineStore(BASELINE_PATH)
app.state.user_directory = UserDirectory(base_url=GRAPH_BASE_URL)
app.state.llm_explainer = LLMExplainer(
    LLMExplainerConfig(
        use_llm=USE_LLM_EXPLAINER,
        service_url=LLM_EXPLAINER_URL,
        timeout_seconds=1.5,
    )
)


@app.on_event("startup")
async def startup() -> None:
    app.state.baseline_store.load()
    try:
        await app.state.user_directory.load()
    except Exception:
        LOGGER.exception("User directory initial load failed")


@app.get("/v1/health")
def health() -> dict:
    baseline_store: BaselineStore = app.state.baseline_store
    user_directory: UserDirectory = app.state.user_directory
    return {
        "status": "ok",
        "baseline_path": str(BASELINE_PATH),
        "baseline_user_count": baseline_store.user_count(),
        "directory_user_count": user_directory.count(),
    }


@app.post("/v1/baseline/reload")
def reload_baseline() -> dict:
    baseline_store: BaselineStore = app.state.baseline_store
    baseline_store.reload()
    return {
        "status": "reloaded",
        "baseline_user_count": baseline_store.user_count(),
        "meta": baseline_store.meta(),
    }


@app.post("/v1/users/reload")
async def reload_users() -> dict:
    user_directory: UserDirectory = app.state.user_directory
    await user_directory.reload()
    return {"status": "reloaded", "directory_user_count": user_directory.count()}


@app.post("/v1/pre-send/check", response_model=PreSendCheckResponse)
async def pre_send_check(payload: PreSendCheckRequest) -> PreSendCheckResponse:
    baseline_store: BaselineStore = app.state.baseline_store
    user_directory: UserDirectory = app.state.user_directory
    llm_explainer: LLMExplainer = app.state.llm_explainer

    sender_baseline = baseline_store.get_sender_baseline(payload.senderUserId)
    result = evaluate_pre_send(payload, sender_baseline, user_directory)

    if result.decision == "ALLOW":
        explanation = build_allow_explanation()
        user_prompt = ""
    else:
        llm_candidates = []
        for candidate in result.confusion_candidates:
            selected_domain = "unknown"
            selected = user_directory.get(candidate.selectedRecipientId)
            if selected is not None and selected.domain:
                selected_domain = selected.domain
            llm_candidates.append(
                {
                    "selectedRecipientName": candidate.selectedRecipientName,
                    "selectedRecipientEmailDomain": selected_domain,
                    "similarKnownRecipientName": candidate.similarKnownRecipientName,
                    "similarity": candidate.similarity,
                }
            )

        llm_result = await llm_explainer.generate_explanation(
            decision=result.decision,
            score=result.score,
            topic=result.topic,
            reasons=result.reasons,
            signals=result.signals,
            confusion_candidates=llm_candidates,
        )
        if llm_result is not None:
            explanation, user_prompt = llm_result
        else:
            explanation, user_prompt = build_fallback_explanation(result.reasons)

    result.signals["user_prompt"] = user_prompt

    return PreSendCheckResponse(
        decision=result.decision,
        score=result.score,
        topic=result.topic,
        reasons=result.reasons,
        signals=result.signals,
        explanation=explanation,
        confusion_candidates=result.confusion_candidates,
    )
