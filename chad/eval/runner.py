from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from chad.eval.registry import (
    BenchmarkDomain,
    BenchmarkSuite,
    BenchmarkTestCase,
    EvaluatorType,
)


@dataclass
class TestCaseResult:
    __test__ = False

    case_id: str
    domain: BenchmarkDomain
    passed: bool
    output: str
    score: float
    latency_ms: float = 0.0
    tokens_used: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "domain": self.domain.value,
            "passed": self.passed,
            "output": self.output,
            "score": self.score,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }


@dataclass
class EvaluationReport:
    suite_name: str
    suite_version: str
    system_version: str
    timestamp: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    domain_scores: dict[str, float]
    results: list[TestCaseResult]
    latency_p50_ms: float
    latency_p95_ms: float
    total_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "suite_version": self.suite_version,
            "system_version": self.system_version,
            "timestamp": self.timestamp,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "pass_rate": self.pass_rate,
            "domain_scores": dict(self.domain_scores),
            "results": [r.to_dict() for r in self.results],
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "total_tokens": self.total_tokens,
        }


class EvaluationRunner:
    """Runner that executes benchmark test cases and compiles evaluation reports."""

    def evaluate_case(
        self,
        case: BenchmarkTestCase,
        executor_fn: Callable[[str, str | None], str | tuple[str, int]],
    ) -> TestCaseResult:
        start_time = time.perf_counter()
        error_msg: str | None = None
        output = ""
        tokens_used = 0

        try:
            raw_res = executor_fn(case.prompt, case.context)
            if isinstance(raw_res, tuple):
                output, tokens_used = raw_res
            else:
                output = raw_res
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            output = ""

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if error_msg is not None:
            return TestCaseResult(
                case_id=case.id,
                domain=case.domain,
                passed=False,
                output=output,
                score=0.0,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                error_message=error_msg,
            )

        passed, score = self._evaluate_output(case, output)
        return TestCaseResult(
            case_id=case.id,
            domain=case.domain,
            passed=passed,
            output=output,
            score=score,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            error_message=None,
        )

    def _evaluate_output(self, case: BenchmarkTestCase, output: str) -> tuple[bool, float]:
        if not output:
            return False, 0.0

        out_lower = output.lower().strip()
        exp_lower = case.expected_output.lower().strip()

        if case.evaluator_type == EvaluatorType.EXACT_MATCH:
            passed = out_lower == exp_lower
            return passed, 1.0 if passed else 0.0

        if case.evaluator_type == EvaluatorType.SUBSTRING:
            passed = exp_lower in out_lower
            return passed, 1.0 if passed else 0.0

        if case.evaluator_type == EvaluatorType.CONTAINS_ALL:
            targets = list(case.criteria) if case.criteria else [case.expected_output]
            matched = sum(1 for target in targets if target.lower() in out_lower)
            score = matched / len(targets) if targets else 0.0
            return score == 1.0, score

        if case.evaluator_type == EvaluatorType.REGEX:
            pattern = case.expected_output
            try:
                matched = re.search(pattern, output, re.IGNORECASE) is not None
                return matched, 1.0 if matched else 0.0
            except re.error:
                return False, 0.0

        if case.evaluator_type == EvaluatorType.CRITERIA:
            targets = list(case.criteria)
            if not targets and case.expected_output:
                targets = [case.expected_output]
            matched = sum(1 for target in targets if target.lower() in out_lower)
            score = matched / len(targets) if targets else 0.0
            return score >= 0.5, score

        # MODEL_JUDGE or default fallback
        passed = exp_lower in out_lower if exp_lower else True
        return passed, 1.0 if passed else 0.0

    def evaluate_suite(
        self,
        suite: BenchmarkSuite,
        executor_fn: Callable[[str, str | None], str | tuple[str, int]],
        system_version: str = "0.1.0",
    ) -> EvaluationReport:
        results: list[TestCaseResult] = []
        domain_totals: dict[str, int] = {}
        domain_passes: dict[str, int] = {}

        latencies: list[float] = []
        total_tokens = 0

        for case in suite.cases.values():
            res = self.evaluate_case(case, executor_fn)
            results.append(res)

            dom_val = case.domain.value
            domain_totals[dom_val] = domain_totals.get(dom_val, 0) + 1
            if res.passed:
                domain_passes[dom_val] = domain_passes.get(dom_val, 0) + 1

            latencies.append(res.latency_ms)
            total_tokens += res.tokens_used

        total_cases = len(results)
        passed_cases = sum(1 for r in results if r.passed)
        pass_rate = (passed_cases / total_cases) if total_cases > 0 else 0.0

        domain_scores = {
            dom: (domain_passes.get(dom, 0) / count)
            for dom, count in domain_totals.items()
        }

        # Calculate latency percentiles
        latencies.sort()
        if latencies:
            p50_idx = max(0, int(len(latencies) * 0.50) - 1)
            p95_idx = max(0, int(len(latencies) * 0.95) - 1)
            p50 = latencies[p50_idx]
            p95 = latencies[p95_idx]
        else:
            p50 = 0.0
            p95 = 0.0

        timestamp = datetime.now(timezone.utc).isoformat()

        return EvaluationReport(
            suite_name=suite.name,
            suite_version=suite.version,
            system_version=system_version,
            timestamp=timestamp,
            total_cases=total_cases,
            passed_cases=passed_cases,
            pass_rate=pass_rate,
            domain_scores=domain_scores,
            results=results,
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            total_tokens=total_tokens,
        )
