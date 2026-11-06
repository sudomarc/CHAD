# ADR 0004: Multi-User Platform Architecture (Authentication, RBAC, Sessions, Ownership, Quotas, Lifecycle)

## Context

CHAD started as a single-tenant agent runtime. Moving toward production web readiness requires multi-user support with tenant isolation, role-based authorization, rate/token quotas, and GDPR-compliant lifecycle management.

## Decision

We introduce the `chad.auth` package and integrate it across application and interface layers:

1. **Authentication and Security (`chad.auth.security`)**:
   - Password hashing with PBKDF2-HMAC-SHA256 (100,000 rounds) using a cryptographically random salt.
   - Constant-time password verification via `hmac.compare_digest`.
   - Secure token generation using standard library `secrets`.

2. **Role-Based Access Control (`chad.auth.models`)**:
   - Explicit `UserRole` taxonomy (`ADMIN`, `MEMBER`, `GUEST`).
   - Granular `Permission` flags covering conversations, runs, tools, connectors, memory, and administration.
   - Deterministic role-to-permission mapping (`ROLE_PERMISSIONS`).

3. **Session Management (`chad.auth.session`)**:
   - Bearer token-based `SessionManager` with configurable TTL, revocation tracking, and expiration purging.

4. **Data Ownership and Tenant Isolation (`chad.auth.ownership`)**:
   - Resource access boundaries enforced by `DataOwnershipManager`.
   - Multi-tenant isolation: members can only read/delete their own resources or explicitly shared resources.
   - Admin bypass for operational governance.

5. **Rate, Token, and Storage Quotas (`chad.auth.quotas`)**:
   - `QuotaManager` enforces sliding-window requests-per-minute limits.
   - Tracks and bounds daily token consumption and storage byte usage per user.

6. **Account Lifecycle & GDPR Anonymization (`chad.auth.lifecycle`)**:
   - `AccountLifecycleManager` ensures complete cascaded deletion upon user request.
   - All active sessions are revoked immediately and owned resources untagged/purged.
   - Audit trail entries replace user identifiers with one-way pseudonymous hashes (`anon_<hash>`) to guarantee GDPR compliance while preserving system auditability.

7. **Web API Integration (`chad.interfaces.web`)**:
   - Endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/quota`, `DELETE /api/auth/account`.
   - Bearer authorization headers parsed and evaluated for access control and quota enforcement.

## Consequences

- Clean separation between identity/tenancy and execution layers.
- Multi-user isolation prevents accidental or malicious data leakage across tenants.
- Clear compliance posture for privacy regulations (GDPR "Right to be Forgotten").
