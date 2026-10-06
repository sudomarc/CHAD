from __future__ import annotations

import pytest

from chad.economics import (
    BudgetExceededError,
    CostCalculator,
    MetricsTracker,
    ModelPricing,
    PricingRegistry,
    UsageBudget,
    UsageMeter,
)


def test_model_pricing_cost_calculation() -> None:
    pricing = ModelPricing(
        model_id="test-model",
        provider="test-prov",
        input_cost_per_million=2.0,
        output_cost_per_million=8.0,
        version="v1",
    )
    cost = pricing.calculate_cost(prompt_tokens=100_000, completion_tokens=50_000)
    # input: (100_000 / 1e6) * 2 = 0.20
    # output: (50_000 / 1e6) * 8 = 0.40
    # total = 0.60
    assert cost == 0.60


def test_pricing_registry_defaults_and_lookup() -> None:
    registry = PricingRegistry()
    lapis_pricing = registry.get_pricing("lapis-v1", "lapis")
    assert lapis_pricing is not None
    assert lapis_pricing.input_cost_per_million == 0.5

    gpt_pricing = registry.get_pricing("gpt-4o", "openai")
    assert gpt_pricing is not None
    assert gpt_pricing.input_cost_per_million == 2.5

    custom_pricing = ModelPricing(
        model_id="custom-model",
        provider="custom",
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )
    registry.register_pricing(custom_pricing)
    assert registry.get_pricing("custom-model", "custom") == custom_pricing

    # Lookup non-existent
    assert registry.get_pricing("non-existent-model", "unknown") is None
    assert registry.calculate_cost("non-existent-model", 1000, 1000, "unknown") == 0.0


def test_cost_calculator() -> None:
    registry = PricingRegistry()
    calculator = CostCalculator(registry)
    cost = calculator.calculate("gpt-4o", 1_000_000, 1_000_000, provider="openai")
    assert cost == 12.50  # 2.50 + 10.0


def test_usage_meter_and_summary() -> None:
    meter = UsageMeter()
    r1 = meter.record_usage(
        record_id="rec-1",
        model_id="gpt-4o",
        provider="openai",
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=150.0,
        conversation_id="conv-1",
        user_id="user-1",
    )
    assert r1.total_tokens == 1500
    assert r1.estimated_cost > 0.0

    r2 = meter.record_usage(
        record_id="rec-2",
        model_id="gpt-4o",
        provider="openai",
        prompt_tokens=2000,
        completion_tokens=1000,
        latency_ms=250.0,
        conversation_id="conv-1",
        user_id="user-1",
    )
    assert r2.total_tokens == 3000

    r3 = meter.record_usage(
        record_id="rec-3",
        model_id="claude-3-5-sonnet",
        provider="anthropic",
        prompt_tokens=5000,
        completion_tokens=2000,
        latency_ms=400.0,
        conversation_id="conv-2",
        user_id="user-2",
    )
    assert r3.total_tokens == 7000

    assert meter.total_tokens(conversation_id="conv-1") == 4500
    assert meter.total_tokens(user_id="user-2") == 7000
    assert meter.total_tokens() == 11500

    summary = meter.summary_by_model()
    assert "gpt-4o" in summary
    assert summary["gpt-4o"]["requests"] == 2
    assert summary["gpt-4o"]["total_tokens"] == 4500
    assert summary["claude-3-5-sonnet"]["requests"] == 1


def test_usage_budget() -> None:
    meter = UsageMeter()
    meter.record_usage(
        record_id="rec-1",
        model_id="gpt-4o",
        provider="openai",
        prompt_tokens=10_000,
        completion_tokens=5_000,
        conversation_id="conv-1",
    )

    token_budget = UsageBudget(max_tokens=20_000, conversation_id="conv-1")
    token_budget.check_budget(meter)
    assert token_budget.remaining_tokens(meter) == 5_000

    exceeded_token_budget = UsageBudget(max_tokens=10_000, conversation_id="conv-1")
    with pytest.raises(BudgetExceededError, match="Token budget exceeded"):
        exceeded_token_budget.check_budget(meter)

    cost_budget = UsageBudget(max_cost_usd=1.00, conversation_id="conv-1")
    cost_budget.check_budget(meter)
    assert cost_budget.remaining_cost(meter) is not None

    exceeded_cost_budget = UsageBudget(max_cost_usd=0.01, conversation_id="conv-1")
    with pytest.raises(BudgetExceededError, match="Cost budget exceeded"):
        exceeded_cost_budget.check_budget(meter)


def test_metrics_tracker_and_percentiles() -> None:
    tracker = MetricsTracker()

    empty_metrics = tracker.get_latency_metrics()
    assert empty_metrics.total_requests == 0
    assert empty_metrics.avg_ms == 0.0

    latencies = [100.0, 200.0, 300.0, 400.0, 500.0]
    for i, lat in enumerate(latencies):
        tracker.record_request(f"req-{i}", "lapis-v1", lat, success=True)

    tracker.record_request("req-err", "lapis-v1", 600.0, success=False, error_type="timeout")

    metrics = tracker.get_latency_metrics("lapis-v1")
    assert metrics.total_requests == 6
    assert metrics.successful_requests == 5
    assert metrics.failed_requests == 1
    assert pytest.approx(metrics.error_rate, 0.01) == 1 / 6
    assert metrics.min_ms == 100.0
    assert metrics.max_ms == 600.0
    assert metrics.p50_ms == 350.0
