from __future__ import annotations

from chad.auth.engine import ApiKeyRecord, AuthEngine, hash_password, verify_password
from chad.auth.lifecycle import AccountLifecycleManager
from chad.auth.models import (
    TIER_LIMITS,
    AccessDeniedError,
    AuthContext,
    AuthError,
    InvalidCredentialsError,
    Permission,
    QuotaExceededError,
    QuotaLimits,
    QuotaUsage,
    RateLimitExceededError,
    SessionExpiredError,
    SessionRecord,
    StorageQuotaExceededError,
    TokenQuotaExceededError,
    User,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRole,
    UserTier,
)
from chad.auth.ownership import DataOwnershipManager, ResourceRecord
from chad.auth.quotas import QuotaManager
from chad.auth.sessions import SessionManager

__all__ = [
    "TIER_LIMITS",
    "AccessDeniedError",
    "AccountLifecycleManager",
    "ApiKeyRecord",
    "AuthContext",
    "AuthEngine",
    "AuthError",
    "DataOwnershipManager",
    "InvalidCredentialsError",
    "Permission",
    "QuotaExceededError",
    "QuotaLimits",
    "QuotaManager",
    "QuotaUsage",
    "RateLimitExceededError",
    "ResourceRecord",
    "SessionExpiredError",
    "SessionManager",
    "SessionRecord",
    "StorageQuotaExceededError",
    "TokenQuotaExceededError",
    "User",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "UserRole",
    "UserTier",
    "hash_password",
    "verify_password",
]
