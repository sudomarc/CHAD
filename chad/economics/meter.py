from __future__ import annotations

import time
from dataclasses import dataclass, field

from chad.economics.pricing import PricingRegistry


@dataclass(frozen=True, slots=True)
class TokenUsageRecord:
    record_id: str
    model_id: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    latency_ms: float = 0.0
    conversation_id: str | None = None
    user_id: str | None = None
    timestamp: float = field(default_factory=time.time)


class CostCalculator:
    def __init__(self, registry: PricingRegistry | None = None) -> None:
        self.registry = registry or PricingRegistry()

    def calculate(
        self,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str = "lapis",
    ) -> float:
        return self.registry.calculate_cost(
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            provider=provider,
        )


class UsageMeter:
    def __init__(self, calculator: CostCalculator | None = None) -> None:
        self.calculator = calculator or CostCalculator()
        self._records: list[TokenUsageRecord] = []

    def record_usage(
        self,
        record_id: str,
        model_id: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float = 0.0,
        conversation_id: str | None = None,
        user_id: str | None = None,
    ) -> TokenUsageRecord:
        total_tokens = prompt_tokens + completion_tokens
        cost = self.calculator.calculate(model_id, prompt_tokens, completion_tokens, provider)
        record = TokenUsageRecord(
            record_id=record_id,
            model_id=model_id,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=cost,
            latency_ms=latency_ms,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        self._records.append(record)
        return record

    def get_records(
        self,
        conversation_id: str | None = None,
        user_id: str | None = None,
    ) -> list[TokenUsageRecord]:
        records = self._records
        if conversation_id is not None:
            records = [r for r in records if r.conversation_id == conversation_id]
        if user_id is not None:
            records = [r for r in records if r.user_id == user_id]
        return list(records)

    def total_tokens(self, conversation_id: str | None = None, user_id: str | None = None) -> int:
        return sum(r.total_tokens for r in self.get_records(conversation_id, user_id))

    def total_cost(self, conversation_id: str | None = None, user_id: str | None = None) -> float:
        return round(
            sum(r.estimated_cost for r in self.get_records(conversation_id, user_id)), 6
        )

    def summary_by_model(self) -> dict[str, dict[str, float | int]]:
        summary: dict[str, dict[str, float | int]] = {}
        for r in self._records:
            if r.model_id not in summary:
                summary[r.model_id] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                }
            item = summary[r.model_id]
            item["requests"] = int(item["requests"]) + 1
            item["prompt_tokens"] = int(item["prompt_tokens"]) + r.prompt_tokens
            item["completion_tokens"] = int(item["completion_tokens"]) + r.completion_tokens
            item["total_tokens"] = int(item["total_tokens"]) + r.total_tokens
            item["total_cost"] = round(float(item["total_cost"]) + r.estimated_cost, 6)
        return summary
