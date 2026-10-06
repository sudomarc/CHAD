from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chad.economics.meter import UsageMeter


class BudgetExceededError(Exception):
    pass


@dataclass(slots=True)
class UsageBudget:
    max_tokens: int | None = None
    max_cost_usd: float | None = None
    conversation_id: str | None = None
    user_id: str | None = None

    def check_budget(self, meter: UsageMeter) -> None:
        total_tokens = meter.total_tokens(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
        )
        if self.max_tokens is not None and total_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {total_tokens} tokens used, limit is {self.max_tokens}."
            )

        total_cost = meter.total_cost(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
        )
        if self.max_cost_usd is not None and total_cost > self.max_cost_usd:
            raise BudgetExceededError(
                f"Cost budget exceeded: ${total_cost:.4f} spent, limit is ${self.max_cost_usd:.4f}."
            )

    def remaining_tokens(self, meter: UsageMeter) -> int | None:
        if self.max_tokens is None:
            return None
        used = meter.total_tokens(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
        )
        return max(0, self.max_tokens - used)

    def remaining_cost(self, meter: UsageMeter) -> float | None:
        if self.max_cost_usd is None:
            return None
        spent = meter.total_cost(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
        )
        return max(0.0, round(self.max_cost_usd - spent, 6))
