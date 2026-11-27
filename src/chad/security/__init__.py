"""Security utilities: secret redaction and safety helpers (M6, issue #77).

Secrets are never persisted or logged in plain text. Redaction is
best-effort pattern-based and applies to text before display/logging.
"""

from .redaction import DEFAULT_SECRET_PATTERNS, Redactor, redact_secrets

__all__ = ["DEFAULT_SECRET_PATTERNS", "Redactor", "redact_secrets"]
