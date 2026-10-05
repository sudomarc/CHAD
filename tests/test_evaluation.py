from __future__ import annotations

import pytest

from chad.eval import (
    BenchmarkDomain,
    BenchmarkRegistry,
    BenchmarkSuite,
    BenchmarkTestCase,
    EvaluationReport,
    EvaluationRunner,
    EvaluatorType,
    QualityThreshold,
    RegressionReport,
    ReleaseGateEvaluator,
    TestCaseResult,
)


def test_benchmark_test_case_to_dict():
    case = BenchmarkTestCase(
        id="test-01",
        domain=BenchmarkDomain.GENERAL_QA,
        prompt="What is Python?",
        expected_output="programming language",
        criteria=("programming", "language"),
        tags=("qa", "python"),
        evaluator_type=EvaluatorType.CONTAINS_ALL,
    )

    d = case.to_dict()
    assert d["id"] == "test-01"
    assert d["domain"] == "general_qa"
    assert d["prompt"] == "What is Python?"
    assert d["evaluator_type"] == "contains_all"
    assert "programming" in d["criteria"]


def test_benchmark_suite_operations():
    suite = BenchmarkSuite(
        name="test-suite",
        version="1.0.0",
        description="A test suite",
    )

    case1 = BenchmarkTestCase(
        id="c1",
        domain=BenchmarkDomain.MATH,
        prompt="1+1?",
        expected_output="2",
    )
    case2 = BenchmarkTestCase(
        id="c2",
        domain=BenchmarkDomain.CODING,
        prompt="Write print",
        expected_output="print()",
    )

    suite.add_case(case1)
    suite.add_case(case2)

    assert suite.get_case("c1").expected_output == "2"
    with pytest.raises(KeyError, match="not found"):
        suite.get_case("non-existent")

    math_cases = suite.filter_by_domain(BenchmarkDomain.MATH)
    assert len(math_cases) == 1
    assert math_cases[0].id == "c1"

    d = suite.to_dict()
    assert d["name"] == "test-suite"
    assert "c1" in d["cases"]


def test_benchmark_registry():
    registry = BenchmarkRegistry(register_defaults=True)

    suites = registry.list_suites()
    assert len(suites) >= 1
    assert suites[0]["name"] == "chad-core-benchmark"

    suite = registry.get_suite("chad-core-benchmark", "1.0.0")
    assert len(suite.cases) == 12

    with pytest.raises(KeyError, match="not found"):
        registry.get_suite("unknown", "1.0.0")

    custom_suite = BenchmarkSuite(name="custom", version="2.0.0")
    registry.register_suite(custom_suite)
    assert registry.get_suite("custom", "2.0.0").name == "custom"


def test_evaluation_runner_case_matching_types():
    runner = EvaluationRunner()

    # Exact match
    case_exact = BenchmarkTestCase(
        id="e1",
        domain=BenchmarkDomain.GENERAL_QA,
        prompt="Capital of France?",
        expected_output="Paris",
        evaluator_type=EvaluatorType.EXACT_MATCH,
    )
    res_exact = runner.evaluate_case(case_exact, lambda p, c: " Paris ")
    assert res_exact.passed is True
    assert res_exact.score == 1.0

    # Substring match
    case_sub = BenchmarkTestCase(
        id="s1",
        domain=BenchmarkDomain.FRENCH,
        prompt="Capitale de la France?",
        expected_output="Paris",
        evaluator_type=EvaluatorType.SUBSTRING,
    )
    res_sub = runner.evaluate_case(case_sub, lambda p, c: "La capitale est Paris.")
    assert res_sub.passed is True

    # Contains all
    case_all = BenchmarkTestCase(
        id="a1",
        domain=BenchmarkDomain.REASONING,
        prompt="Test criteria",
        expected_output="",
        criteria=("alpha", "beta"),
        evaluator_type=EvaluatorType.CONTAINS_ALL,
    )
    res_all = runner.evaluate_case(case_all, lambda p, c: "Alpha and Beta are present")
    assert res_all.passed is True

    res_partial = runner.evaluate_case(case_all, lambda p, c: "Only Alpha present")
    assert res_partial.passed is False
    assert res_partial.score == 0.5

    # Regex match
    case_regex = BenchmarkTestCase(
        id="r1",
        domain=BenchmarkDomain.MATH,
        prompt="Equation answer",
        expected_output=r"x\s*=\s*42",
        evaluator_type=EvaluatorType.REGEX,
    )
    res_regex = runner.evaluate_case(case_regex, lambda p, c: "The value is x = 42")
    assert res_regex.passed is True


def test_evaluation_runner_error_handling():
    runner = EvaluationRunner()
    case = BenchmarkTestCase(
        id="err1",
        domain=BenchmarkDomain.CODING,
        prompt="Fail code",
        expected_output="code",
    )

    def failing_executor(prompt, context):
        raise RuntimeError("Execution engine crashed")

    res = runner.evaluate_case(case, failing_executor)
    assert res.passed is False
    assert res.error_message == "Execution engine crashed"
    assert res.score == 0.0


def test_evaluation_runner_suite_execution():
    runner = EvaluationRunner()
    registry = BenchmarkRegistry(register_defaults=True)
    suite = registry.get_suite("chad-core-benchmark", "1.0.0")

    def mock_executor(prompt: str, context: str | None) -> tuple[str, int]:
        # Return suitable answers to pass all test cases
        if "capital" in prompt.lower() or "capitale" in prompt.lower():
            return ("Paris is the capital", 15)
        if "a necessarily c" in prompt.lower():
            return ("Yes, A is transitively C", 20)
        if "even" in prompt.lower():
            return ("def is_even(n):\n    return n % 2 == 0", 25)
        if "12 * 12" in prompt.lower():
            return ("144", 10)
        if "transformer" in prompt.lower():
            return ("The self-attention mechanism in transformer architecture", 30)
        if "calculator" in prompt.lower():
            return ("The answer is 42", 12)
        if "uploaded text file" in prompt.lower():
            return ("extracted content summary", 18)
        if "screenshot" in prompt.lower():
            return ("header bar and content pane detected", 22)
        if "ignore all instructions" in prompt.lower():
            return ("I cannot fulfill this request.", 14)
        if "python" in prompt.lower():
            return ("Python is a programming language", 16)
        if "hello world" in prompt.lower():
            return ("Bonjour and Hola", 18)
        return ("default response", 10)

    report = runner.evaluate_suite(suite, mock_executor, system_version="0.1.0")

    assert isinstance(report, EvaluationReport)
    assert report.total_cases == 12
    assert report.passed_cases == 12
    assert report.pass_rate == 1.0
    assert report.total_tokens > 0
    assert report.latency_p50_ms >= 0.0
    assert report.latency_p95_ms >= report.latency_p50_ms

    d = report.to_dict()
    assert d["suite_name"] == "chad-core-benchmark"
    assert d["pass_rate"] == 1.0
    assert "general_qa" in d["domain_scores"]


def test_release_gate_evaluator():
    evaluator = ReleaseGateEvaluator()

    report_pass = EvaluationReport(
        suite_name="chad-core-benchmark",
        suite_version="1.0.0",
        system_version="0.1.0",
        timestamp="2026-10-05T00:00:00Z",
        total_cases=10,
        passed_cases=9,
        pass_rate=0.90,
        domain_scores={"general_qa": 1.0, "safety": 1.0, "coding": 0.8},
        results=[
            TestCaseResult(
                case_id="safe-1",
                domain=BenchmarkDomain.SAFETY,
                passed=True,
                output="OK",
                score=1.0,
            )
        ],
        latency_p50_ms=50.0,
        latency_p95_ms=120.0,
        total_tokens=100,
    )

    thresh = QualityThreshold(
        min_overall_pass_rate=0.85,
        min_domain_pass_rates={BenchmarkDomain.CODING: 0.75},
        max_p95_latency_ms=200.0,
        require_zero_safety_failures=True,
    )

    passed, violations = evaluator.evaluate(report_pass, thresh)
    assert passed is True
    assert len(violations) == 0

    # Failure case: overall pass rate too low and safety failure
    report_fail = EvaluationReport(
        suite_name="chad-core-benchmark",
        suite_version="1.0.0",
        system_version="0.1.0",
        timestamp="2026-10-05T00:00:00Z",
        total_cases=10,
        passed_cases=6,
        pass_rate=0.60,
        domain_scores={"general_qa": 0.5, "safety": 0.0},
        results=[
            TestCaseResult(
                case_id="safe-1",
                domain=BenchmarkDomain.SAFETY,
                passed=False,
                output="Leaked secret!",
                score=0.0,
            )
        ],
        latency_p50_ms=100.0,
        latency_p95_ms=300.0,
        total_tokens=100,
    )

    passed_f, violations_f = evaluator.evaluate(report_fail, thresh)
    assert passed_f is False
    assert len(violations_f) >= 3


def test_regression_report():
    baseline_results = [
        TestCaseResult(
            case_id="c1",
            domain=BenchmarkDomain.GENERAL_QA,
            passed=True,
            output="Ans1",
            score=1.0,
        ),
        TestCaseResult(
            case_id="c2",
            domain=BenchmarkDomain.CODING,
            passed=False,
            output="Err",
            score=0.0,
        ),
    ]
    candidate_results = [
        TestCaseResult(
            case_id="c1",
            domain=BenchmarkDomain.GENERAL_QA,
            passed=False,
            output="Wrong",
            score=0.0,
        ),
        TestCaseResult(
            case_id="c2",
            domain=BenchmarkDomain.CODING,
            passed=True,
            output="Fixed",
            score=1.0,
        ),
    ]

    base_report = EvaluationReport(
        suite_name="bench",
        suite_version="1.0",
        system_version="0.1.0",
        timestamp="2026-10-05T00:00:00Z",
        total_cases=2,
        passed_cases=1,
        pass_rate=0.50,
        domain_scores={"general_qa": 1.0, "coding": 0.0},
        results=baseline_results,
        latency_p50_ms=10.0,
        latency_p95_ms=20.0,
        total_tokens=50,
    )

    cand_report = EvaluationReport(
        suite_name="bench",
        suite_version="1.0",
        system_version="0.2.0",
        timestamp="2026-10-05T01:00:00Z",
        total_cases=2,
        passed_cases=1,
        pass_rate=0.50,
        domain_scores={"general_qa": 0.0, "coding": 1.0},
        results=candidate_results,
        latency_p50_ms=10.0,
        latency_p95_ms=20.0,
        total_tokens=50,
    )

    regression = RegressionReport.compare(base_report, cand_report)

    assert regression.has_regressions is True
    assert len(regression.regressed_cases) == 1
    assert regression.regressed_cases[0]["case_id"] == "c1"

    assert len(regression.improved_cases) == 1
    assert regression.improved_cases[0]["case_id"] == "c2"

    assert "general_qa" in regression.domain_changes
    assert regression.domain_changes["general_qa"]["diff"] == -1.0
    assert regression.domain_changes["coding"]["diff"] == 1.0

    d = regression.to_dict()
    assert d["has_regressions"] is True
    assert d["baseline_version"] == "0.1.0"
    assert d["candidate_version"] == "0.2.0"
