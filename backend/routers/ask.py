"""
AI conversation endpoint - ask questions about freight exceptions.
AI 对话端点 - 针对货运异常提问
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter()

MODELS = {
    "sea": "SeaException",
    "road": "RoadException",
    "air": "AirException",
}


def _get_exception_context(db, mode, exception_id):
    """Load an exception and return a compact context string for the LLM."""
    if mode == "sea":
        from sea_freight_models import SeaException as Model
    elif mode == "road":
        from road_freight_models import RoadException as Model
    elif mode == "air":
        from air_cargo_models import AirException as Model
    else:
        return ""

    exc = db.query(Model).filter(Model.exception_id == exception_id).first()
    if not exc:
        return ""

    parts = [
        f"Exception type: {exc.exception_type}",
        f"Category: {exc.exception_category or 'unknown'}",
        f"Root cause: {exc.root_cause or 'unknown'}",
        f"Root cause category: {exc.root_cause_category or 'unknown'}",
        f"AI diagnosis: {exc.ai_diagnosis or 'unknown'}",
        f"Risk level: {exc.risk_level}, severity: {exc.severity}, status: {exc.status}",
        f"Recommended action: {exc.recommended_action or 'none'}",
        f"Recovery options: {exc.recovery_options or '[]'}",
        f"Predicted downstream impact: {exc.predicted_downstream_impact or 'unknown'}",
        f"Estimated recovery cost: ${exc.recovery_cost:.0f}" if exc.recovery_cost else "Recovery cost: unknown",
    ]
    return "\n".join(parts)


@router.post("/ask")
async def ask(body: dict, db: Session = Depends(get_db)):
    """
    Ask the AI about a freight exception (or a general freight question).

    Body:
        {"question": "...", "mode": "sea|road|air", "exception_id": "EXC-SIM-..."}

    When mode + exception_id are provided, the exception's context is loaded
    and included so the AI can answer specifically about that case.
    """
    from llm_client import chat, is_available, SYSTEM_PROMPT

    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    mode = body.get("mode")
    exception_id = body.get("exception_id")

    context = ""
    if mode and exception_id:
        context = _get_exception_context(db, mode, exception_id)
        if not context:
            raise HTTPException(status_code=404, detail="exception not found")

    if not is_available():
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set DEEPSEEK_API_KEY and llm_enabled=true",
        )

    user_prompt = question
    if context:
        user_prompt = f"Here is a freight exception to assess:\n{context}\n\nQuestion: {question}"

    answer = chat(SYSTEM_PROMPT, user_prompt)
    if answer is None:
        raise HTTPException(status_code=502, detail="LLM request failed")

    return {
        "answer": answer,
        "mode": mode,
        "exception_id": exception_id,
    }
