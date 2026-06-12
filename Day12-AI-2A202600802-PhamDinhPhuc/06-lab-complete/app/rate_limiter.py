"""Redis-backed sliding-window rate limiter."""
import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.storage import redis_client


WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> dict:
    key = f"rate:{user_id}"
    now = time.time()
    member = f"{now}:{uuid.uuid4().hex}"

    try:
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW_SECONDS)
        results = pipe.execute()
        request_count = int(results[2])
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc

    if request_count > settings.rate_limit_per_minute:
        redis_client.zrem(key, member)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
            },
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": max(0, settings.rate_limit_per_minute - request_count),
        "window_seconds": WINDOW_SECONDS,
    }
