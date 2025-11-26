"""Redis-backed token bucket rate limiter."""

import time
import math
from typing import Optional

import redis

from app.config import settings
from app.utils.logger import log


class RedisRateLimiter:
    """Token-bucket limiter using Redis for distributed enforcement."""

    def __init__(self, key_prefix: str, rate_limit: int, time_window: int = 60):
        self.key_prefix = key_prefix
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.redis = redis.Redis.from_url(settings.redis_url)

    def _keys(self, scope: str):
        base = f"rate:{self.key_prefix}:{scope}"
        return base + ":tokens", base + ":updated"

    def acquire(self, scope: str) -> bool:
        """Attempt to acquire a token. Returns True if allowed, else False."""
        tokens_key, updated_key = self._keys(scope)
        pipe = self.redis.pipeline()
        now = time.time()

        # Fetch current state
        pipe.get(tokens_key)
        pipe.get(updated_key)
        current_tokens, last_update = pipe.execute()

        try:
            current_tokens = float(current_tokens) if current_tokens is not None else float(self.rate_limit)
        except Exception:
            current_tokens = float(self.rate_limit)
        try:
            last_update = float(last_update) if last_update is not None else now
        except Exception:
            last_update = now

        # Refill based on elapsed time
        elapsed = max(0.0, now - last_update)
        refill_rate = self.rate_limit / self.time_window
        new_tokens = min(self.rate_limit, current_tokens + elapsed * refill_rate)

        allowed = new_tokens >= 1.0
        if allowed:
            new_tokens -= 1.0
        else:
            log.warning(f"Rate limit hit for {scope}; tokens={new_tokens:.2f}")

        # Persist state
        pipe = self.redis.pipeline()
        pipe.set(tokens_key, new_tokens)
        pipe.set(updated_key, now)
        pipe.execute()

        return allowed
