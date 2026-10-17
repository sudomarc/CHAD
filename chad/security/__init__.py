"""CHAD security module (Phase 14). Provides threat modeling, prompt injection detection,

retrieval poisoning defense, exfiltration protection, secret masking, sandbox escape guards,
and a unified SecurityEngine.
"""

from chad.security.engine import SecurityAuditLog, SecurityCheckResult, SecurityEngine
from chad.security.escape import EscapeAnalysis, SandboxEscapeGuard
from chad.security.exfiltration import (
    ExfiltrationAnalysis,
    ExfiltrationCategory,
    ExfiltrationProtection,
)
from chad.security.injection import (
    InjectionDetectionResult,
    PoisoningAnalysisResult,
    PromptInjectionDetector,
    RetrievalPoisoningGuard,
)
from chad.security.threat import SecurityThreat, ThreatCategory, ThreatLevel, ThreatModel

__all__ = [
    "EscapeAnalysis",
    "ExfiltrationAnalysis",
    "ExfiltrationCategory",
    "ExfiltrationProtection",
    "InjectionDetectionResult",
    "PoisoningAnalysisResult",
    "PromptInjectionDetector",
    "RetrievalPoisoningGuard",
    "SandboxEscapeGuard",
    "SecurityAuditLog",
    "SecurityCheckResult",
    "SecurityEngine",
    "SecurityThreat",
    "ThreatCategory",
    "ThreatLevel",
    "ThreatModel",
]
