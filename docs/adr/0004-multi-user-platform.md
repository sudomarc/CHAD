# ADR 0004: Multi-User Platform, Authentication, Tenant Isolation, and Quota Management

## Context

CHAD is evolving into a full-featured agentic runtime capable of rivaling platforms like ChatGPT and Claude.
To support individual users, teams, and enterprise deployments, the application runtime requires:
1. Multi-user identity management, credential security, and role-based access control (RBAC).
2. Strict data ownership and multi-tenant isolation across conversations, files, memories, and agent tasks.
3. Session management with lifecycle controls and instant revocation.
4. Tiered resource limits and rate/token/storage quotas to prevent resource exhaustion and abuse.
5. GDPR-compliant account lifecycle management (Right to Be Forgotten) with cascade data deletion and cryptographic audit trail boundary anonymization.

## Decision

We introduce a dedicated multi-user platform module (`chad.auth`) with six cohesive components:

1. **User Identity & RBAC (`chad.auth.models`, `chad.auth.engine`)**:
   - `User` entity with `UserRole` (`ADMIN`, `MEMBER`, `GUEST`) and `UserTier` (`FREE`, `PRO`, `ENTERPRISE`).
   - Salted PBKDF2-HMAC-SHA256 password hashing and secure token generation for API keys (`chad_live_...`).
   - Fine-grained `Permission` evaluation (`has_permission`, `assert_permission`).

2. **Session Lifecycle (`chad.auth.sessions`)**:
   - `SessionManager` managing active sessions with SHA-256 token hashing, configurable TTL, activity extensions, and single/all-session revocation.

3. **Data Ownership & Tenant Isolation (`chad.auth.ownership`)**:
   - `DataOwnershipManager` enforcing strict boundary isolation (`check_access`, `assert_access`).
   - Conversations and state are explicitly tagged with `owner_id`.
   - Cross-user data access is denied with `AccessDeniedError` unless an administrative override is authorized and audited.

4. **Tiered Quota Enforcement (`chad.auth.quotas`)**:
   - `QuotaManager` monitoring sliding-window request rates per minute (`RateLimitExceededError`), daily token consumption (`TokenQuotaExceededError`), and byte-level storage capacity (`StorageQuotaExceededError`).

5. **GDPR Account Deletion & Audit Boundary (`chad.auth.lifecycle`)**:
   - `AccountLifecycleManager` orchestrating cascade deletion across sessions, conversation stores, memory items, and user records.
   - Irreversible pseudonymization of user identities in audit trails (`[ANONYMIZED_USER:<hash>]`), preserving log integrity while removing PII.

6. **Web API Integration (`chad.interfaces.web`)**:
   - Bearer token authentication supporting both session tokens and API keys.
   - User-scoped conversation retrieval and management.
   - Quota enforcement on chat generation endpoints.
   - Public auth endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/quota`, `DELETE /api/auth/account`.

## Consequences

- Provides secure multi-user tenancy and privacy isolation across all application layers.
- Prevents denial-of-service and runaway inference costs via tiered rate and token limits.
- Meets GDPR right-to-be-forgotten requirements without compromising audit security.
- Preserves full backward-compatibility for unauthenticated or single-user local CLI runs.

## Verification

- Verified through unit and integration test suite in `tests/test_auth.py`.
- Tested in end-to-end HTTP web server flows with full quota and tenant isolation checks.
