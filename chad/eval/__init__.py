"""CHAD evaluation, benchmark registry, and release gates (Phase 15)."""

from chad.eval.gates import QualityThreshold, RegressionReport, ReleaseGateEvaluator
from chad.eval.registry import (
    BenchmarkDomain,
    BenchmarkRegistry,
    BenchmarkSuite,
    BenchmarkTestCase,
    EvaluatorType,
)
from chad.eval.runner import EvaluationReport, EvaluationRunner, TestCaseResult

__all__ = [
    "BenchmarkDomain",
    "BenchmarkRegistry",
    "BenchmarkSuite",
    "BenchmarkTestCase",
    "EvaluationReport",
    "EvaluationRunner",
    "EvaluatorType",
    "QualityThreshold",
    "RegressionReport",
    "ReleaseGateEvaluator",
    "TestCaseResult",
]
