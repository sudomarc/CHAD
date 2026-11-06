from __future__ import annotations

import time
from collections import defaultdict, deque

from chad.auth.models import User


class QuotaExceededError(Exception):
    """Raised when request rate, token, or storage quota is exceeded."""


class QuotaManager:
    """Tracks and enforces rate, token, and storage quotas per user."""

    def __init__(self) -> None:
        # user_id -> deque of timestamps (seconds)
        self._request_history: dict[str, deque[float]] = defaultdict(deque)

    def check_rate_limit(self, user: User, now: float | None = None) -> bool:
        current_time = time.time() if now is None else now
        history = self._request_history[user.id]

        # Evict timestamps older than 60 seconds
        cutoff = current_time - 60.0
        while history and history[0] < cutoff:
            history.popleft()

        limit = user.quotas.requests_per_minute
        if len(history) >= limit:
            return False

        history.append(current_time)
        return True

    def require_rate_limit(self, user: User, now: float | None = None) -> None:
        if not self.check_rate_limit(user, now):
            raise QuotaExceededError(
                f"Rate limit exceeded: user {user.username} has exceeded {user.quotas.requests_per_minute} requests/minute."
            )

    def check_token_quota(self, user: User, tokens_to_consume: int) -> bool:
        return (user.quotas.used_tokens_today + tokens_to_consume) <= user.quotas.max_tokens_per_day

    def record_tokens(self, user: User, tokens: int) -> None:
        if not self.check_token_quota(user, tokens):
            raise QuotaExceededError(
                f"Token quota exceeded: user {user.username} would exceed daily limit of {user.quotas.max_tokens_per_day} tokens."
            )
        user.quotas.used_tokens_today += tokens

    def check_storage_quota(self, user: User, additional_bytes: int) -> bool:
        return (user.quotas.used_storage_bytes + additional_bytes) <= user.quotas.max_storage_bytes

    def record_storage(self, user: User, additional_bytes: int) -> None:
        if not self.check_storage_quota(user, additional_bytes):
            raise QuotaExceededError(
                f"Storage quota exceeded: user {user.username} would exceed max limit of {user.quotas.max_storage_bytes} bytes."
            )
        user.quotas.used_storage_bytes += additional_bytes

    def release_storage(self, user: User, freed_bytes: int) -> None:
        user.quotas.used_storage_bytes = max(0, user.quotas.used_storage_bytes - freed_bytes)

    def reset_daily_tokens(self, user: User) -> None:
        user.quotas.used_tokens_today = 0
