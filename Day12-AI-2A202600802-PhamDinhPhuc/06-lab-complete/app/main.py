"""Production AI Agent for the Day 12 final lab."""
import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, charge_budget, estimate_cost, get_budget_status
from app.rate_limiter import check_rate_limit
from app.storage import redis_client
from utils.mock_llm import ask as llm_ask


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0


def _history_key(user_id: str) -> str:
    return f"history:{user_id}"


def load_history(user_id: str) -> list[dict]:
    raw_items = redis_client.lrange(_history_key(user_id), 0, -1)
    history = []
    for item in raw_items:
        try:
            history.append(json.loads(item))
        except json.JSONDecodeError:
            logger.warning(json.dumps({"event": "bad_history_item", "user_id": user_id}))
    return history


def append_history(user_id: str, role: str, content: str) -> None:
    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    key = _history_key(user_id)
    pipe = redis_client.pipeline()
    pipe.rpush(key, json.dumps(entry, ensure_ascii=False))
    pipe.ltrim(key, -settings.max_history_messages, -1)
    pipe.expire(key, settings.history_ttl_seconds)
    pipe.execute()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    redis_client.ping()
    _is_ready = True
    logger.info(json.dumps({"event": "ready", "redis": "ok"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception:
        _error_count += 1
        raise


class AskRequest(BaseModel):
    user_id: str = Field("default-user", min_length=1, max_length=100)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_length: int
    usage: dict
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
            "metrics": "GET /metrics (requires X-API-Key)",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _api_key: str = Depends(verify_api_key),
):
    rate_info = check_rate_limit(body.user_id)

    history = load_history(body.user_id)
    append_history(body.user_id, "user", body.question)
    input_tokens = len(body.question.split()) * 2
    check_budget(body.user_id, estimate_cost(input_tokens=input_tokens, output_tokens=0))

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
        "history_messages": len(history),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    answer = llm_ask(body.question)
    append_history(body.user_id, "assistant", answer)

    output_tokens = len(answer.split()) * 2
    usage = charge_budget(
        body.user_id,
        estimate_cost(input_tokens=input_tokens, output_tokens=output_tokens),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        history_length=len(load_history(body.user_id)),
        usage={
            "requests_remaining": rate_info["remaining"],
            "monthly_cost_usd": usage["monthly_cost_usd"],
            "monthly_budget_usd": usage["monthly_budget_usd"],
            "budget_remaining_usd": usage["budget_remaining_usd"],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{user_id}", tags=["Agent"])
def get_history(user_id: str, _api_key: str = Depends(verify_api_key)):
    history = load_history(user_id)
    return {
        "user_id": user_id,
        "messages": history,
        "count": len(history),
    }


@app.get("/health", tags=["Operations"])
def health():
    checks = {"llm": "mock" if not settings.openai_api_key else "openai"}
    try:
        redis_client.ping()
        checks["redis"] = "ok"
        status = "ok"
    except Exception:
        checks["redis"] = "unavailable"
        status = "degraded"

    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready")
    try:
        redis_client.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Redis not ready") from exc
    return {"ready": True, "redis": "ok"}


@app.get("/metrics", tags=["Operations"])
def metrics(_api_key: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "monthly_budget_usd": settings.monthly_budget_usd,
        "storage": "redis",
    }


@app.get("/usage/{user_id}", tags=["Operations"])
def usage(user_id: str, _api_key: str = Depends(verify_api_key)):
    return get_budget_status(user_id)


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
