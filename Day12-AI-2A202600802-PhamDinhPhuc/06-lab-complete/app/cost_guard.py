"""Redis-backed monthly budget guard."""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.storage import redis_client


PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006
MONTH_TTL_SECONDS = 32 * 24 * 60 * 60


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
        + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    )


def _usage_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def _usage_value(user_id: str) -> float:
    raw = redis_client.get(_usage_key(user_id))
    return float(raw or 0)


def check_budget(user_id: str, estimated_cost_usd: float = 0.0) -> dict:
    try:
        current = _usage_value(user_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Budget guard unavailable") from exc

    projected = current + estimated_cost_usd
    if projected > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "projected_usd": round(projected, 6),
                "budget_usd": settings.monthly_budget_usd,
            },
        )
    return {
        "monthly_cost_usd": round(current, 6),
        "monthly_budget_usd": settings.monthly_budget_usd,
        "budget_remaining_usd": round(settings.monthly_budget_usd - current, 6),
    }


def charge_budget(
    user_id: str,
    cost_usd: float,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    check_budget(user_id, cost_usd)
    key = _usage_key(user_id)
    token_key = f"{key}:tokens"
    try:
        pipe = redis_client.pipeline()
        pipe.incrbyfloat(key, cost_usd)
        pipe.expire(key, MONTH_TTL_SECONDS)
        pipe.hincrby(token_key, "input_tokens", input_tokens)
        pipe.hincrby(token_key, "output_tokens", output_tokens)
        pipe.expire(token_key, MONTH_TTL_SECONDS)
        results = pipe.execute()
        monthly_cost = float(results[0])
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Budget guard unavailable") from exc

    return {
        "monthly_cost_usd": round(monthly_cost, 6),
        "monthly_budget_usd": settings.monthly_budget_usd,
        "budget_remaining_usd": round(settings.monthly_budget_usd - monthly_cost, 6),
    }


def get_budget_status(user_id: str) -> dict:
    status = check_budget(user_id)
    token_key = f"{_usage_key(user_id)}:tokens"
    tokens = redis_client.hgetall(token_key)
    return {
        "user_id": user_id,
        **status,
        "input_tokens": int(tokens.get("input_tokens", 0)),
        "output_tokens": int(tokens.get("output_tokens", 0)),
    }
