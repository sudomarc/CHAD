from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chad.eval.registry import BenchmarkDomain
from chad.eval.runner import EvaluationReport


@dataclass
class QualityThreshold:
    min_overall_pass_rate: float = 0.80
    min_domain_pass_rates: dict[BenchmarkDomain | str, float] = field(default_factory=dict)
    max_p95_latency_ms: float | None = None
    require_zero_safety_failures: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_overall_pass_rate": self.min_overall_pass_rate,
            "min_domain_pass_rates": {
                (k.value if isinstance(k, BenchmarkDomain) else k): v
                for k, v in self.min_domain_pass_rates.items()
            },
            "max_p95_latency_ms": self.max_p95_latency_ms,
            "require_zero_safety_failures": self.require_zero_safety_failures,
        }


class ReleaseGateEvaluator:
    """Evaluates benchmark reports against quality thresholds for release gating."""

    def evaluate(
        self,
        report: EvaluationReport,
        threshold: QualityThreshold | None = None,
    ) -> tuple[bool, list[str]]:
        thresh = threshold or QualityThreshold()
        violations: list[str] = []

        # 1. Overall pass rate check
        if report.pass_rate < thresh.min_overall_pass_rate:
            violations.append(
                f"Overall pass rate {report.pass_rate:.2%} is below required threshold {thresh.min_overall_pass_rate:.2%}."
            )

        # 2. Domain pass rate checks
        for dom, min_rate in thresh.min_domain_pass_rates.items():
            dom_key = dom.value if isinstance(dom, BenchmarkDomain) else dom
            actual_rate = report.domain_scores.get(dom_key, 0.0)
            if actual_rate < min_rate:
                violations.append(
                    f"Domain '{dom_key}' pass rate {actual_rate:.2%} is below required threshold {min_rate:.2%}."
                )

        # 3. Safety check
        if thresh.require_zero_safety_failures:
            safety_key = BenchmarkDomain.SAFETY.value
            safety_failures = [
                r for r in report.results if r.domain.value == safety_key and not r.passed
            ]
            if safety_failures:
                failed_ids = ", ".join(r.case_id for r in safety_failures)
                violations.append(
                    f"Safety quality threshold violated: {len(safety_failures)} safety test case(s) failed ({failed_ids})."
                )

        # 4. Latency p95 check
        if (
            thresh.max_p95_latency_ms is not None
            and report.latency_p95_ms > thresh.max_p95_latency_ms
        ):
            violations.append(
                f"Latency p95 {report.latency_p95_ms:.2f}ms exceeds maximum allowed threshold {thresh.max_p95_latency_ms:.2f}ms."
            )

        passed = len(violations) == 0
        return passed, violations


@dataclass
class RegressionReport:
    baseline_version: str
    candidate_version: str
    regressed_cases: list[dict[str, Any]] = field(default_factory=list)
    improved_cases: list[dict[str, Any]] = field(default_factory=list)
    domain_changes: dict[str, dict[str, float]] = field(default_factory=dict)
    has_regressions: bool = False

    @classmethod
    def compare(
        cls,
        baseline: EvaluationReport,
        candidate: EvaluationReport,
    ) -> RegressionReport:
        baseline_cases = {r.case_id: r for r in baseline.results}
        candidate_cases = {r.case_id: r for r in candidate.results}

        regressed: list[dict[str, Any]] = []
        improved: list[dict[str, Any]] = []

        all_ids = set(baseline_cases.keys()) | set(candidate_cases.keys())
        for case_id in sorted(all_ids):
            base_r = baseline_cases.get(case_id)
            cand_r = candidate_cases.get(case_id)

            if base_r and cand_r:
                if base_r.passed and not cand_r.passed:
                    regressed.append(
                        {
                            "case_id": case_id,
                            "domain": cand_r.domain.value,
                            "baseline_score": base_r.score,
                            "candidate_score": cand_r.score,
                        }
                    )
                elif not base_r.passed and cand_r.passed:
                    improved.append(
                        {
                            "case_id": case_id,
                            "domain": cand_r.domain.value,
                            "baseline_score": base_r.score,
                            "candidate_score": cand_r.score,
                        }
                    )

        # Domain level changes
        all_domains = set(baseline.domain_scores.keys()) | set(candidate.domain_scores.keys())
        domain_changes: dict[str, dict[str, float]] = {}
        for dom in sorted(all_domains):
            base_score = baseline.domain_scores.get(dom, 0.0)
            cand_score = candidate.domain_scores.get(dom, 0.0)
            diff = cand_score - base_score
            domain_changes[dom] = {
                "baseline_pass_rate": base_score,
                "candidate_pass_rate": cand_score,
                "diff": diff,
            }

        has_regressions = len(regressed) > 0

        return cls(
            baseline_version=baseline.system_version,
            candidate_version=candidate.system_version,
            regressed_cases=regressed,
            improved_cases=improved,
            domain_changes=domain_changes,
            has_regressions=has_regressions,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_version": self.baseline_version,
            "candidate_version": self.candidate_version,
            "regressed_cases": self.regressed_cases,
            "improved_cases": self.improved_cases,
            "domain_changes": self.domain_changes,
            "has_regressions": self.has_regressions,
        }
