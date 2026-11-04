from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from chad.auth.models import (
    TIER_LIMITS,
    QuotaLimits,
    QuotaUsage,
    RateLimitExceededError,
    StorageQuotaExceededError,
    TokenQuotaExceededError,
    User,
    UserTier,
)


@dataclass(slots=True)
class UserUsageState:
    request_timestamps: list[float] = field(default_factory=list)
    daily_tokens: int = 0
    daily_tokens_date: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d")
    )
    storage_bytes: int = 0
    active_tasks: int = 0


class QuotaManager:
    """Monitors and enforces rate, token, and storage quotas per user tier."""

    def __init__(
        self,
        custom_tier_limits: dict[UserTier, QuotaLimits] | None = None,
        rate_window_seconds: float = 60.0,
    ) -> None:
        self.tier_limits = dict(custom_tier_limits or TIER_LIMITS)
        self.rate_window_seconds = rate_window_seconds
        self._usage: dict[str, UserUsageState] = defaultdict(UserUsageState)

    def get_limits(self, user: User) -> QuotaLimits:
        return self.tier_limits.get(user.tier, TIER_LIMITS[UserTier.FREE])

    def _get_state(self, user_id: str) -> UserUsageState:
        state = self._usage[user_id]
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if state.daily_tokens_date != today:
            state.daily_tokens = 0
            state.daily_tokens_date = today
        return state

    def check_request_quota(self, user: User) -> None:
        limits = self.get_limits(user)
        state = self._get_state(user.id)
        now = time.time()
        cutoff = now - self.rate_window_seconds

        # Prune old request timestamps
        state.request_timestamps = [ts for ts in state.request_timestamps if ts > cutoff]

        if len(state.request_timestamps) >= limits.requests_per_minute:
            raise RateLimitExceededError(
                f"Rate limit exceeded for user '{user.username}': "
                f"limit is {limits.requests_per_minute} req/min."
            )

    def record_request(self, user: User) -> None:
        self.check_request_quota(user)
        state = self._get_state(user.id)
        state.request_timestamps.append(time.time())

    def check_and_record_tokens(self, user: User, tokens: int) -> None:
        if tokens <= 0:
            return
        limits = self.get_limits(user)
        state = self._get_state(user.id)

        if state.daily_tokens + tokens > limits.tokens_per_day:
            raise TokenQuotaExceededError(
                f"Daily token quota exceeded for user '{user.username}': "
                f"{state.daily_tokens + tokens} requested, limit is {limits.tokens_per_day} tokens/day."
            )
        state.daily_tokens += tokens

    def check_storage_quota(self, user: User, additional_bytes: int = 0) -> None:
        limits = self.get_limits(user)
        state = self._get_state(user.id)
        total = state.storage_bytes + max(0, additional_bytes)
        if total > limits.storage_bytes:
            raise StorageQuotaExceededError(
                f"Storage quota exceeded for user '{user.username}': "
                f"{total} bytes requested, limit is {limits.storage_bytes} bytes."
            )

    def record_storage(self, user: User, bytes_delta: int) -> None:
        if bytes_delta > 0:
            self.check_storage_quota(user, bytes_delta)
        state = self._get_state(user.id)
        state.storage_bytes = max(0, state.storage_bytes + bytes_delta)

    def get_quota_usage(self, user: User) -> QuotaUsage:
        limits = self.get_limits(user)
        state = self._get_state(user.id)
        now = time.time()
        cutoff = now - self.rate_window_seconds
        recent_reqs = sum(1 for ts in state.request_timestamps if ts > cutoff)

        return QuotaUsage(
            user_id=user.id,
            requests_count=recent_reqs,
            tokens_used=state.daily_tokens,
            storage_used_bytes=state.storage_bytes,
            limits=limits,
        )

    def reset_user(self, user_id: str) -> None:
        self._usage.pop(user_id, None)
