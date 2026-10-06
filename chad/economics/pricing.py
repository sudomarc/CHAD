from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPricing:
    model_id: str
    provider: str = "lapis"
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    version: str = "v1"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        input_cost = (prompt_tokens / 1_000_000.0) * self.input_cost_per_million
        output_cost = (completion_tokens / 1_000_000.0) * self.output_cost_per_million
        return round(input_cost + output_cost, 6)


class PricingRegistry:
    def __init__(self) -> None:
        self._pricing: dict[tuple[str, str], ModelPricing] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            ModelPricing("lapis-v1", "lapis", 0.5, 1.5, "v1"),
            ModelPricing("gpt-4o", "openai", 2.5, 10.0, "v1"),
            ModelPricing("claude-3-5-sonnet", "anthropic", 3.0, 15.0, "v1"),
            ModelPricing("gemini-1.5-pro", "google", 1.25, 5.0, "v1"),
        ]
        for p in defaults:
            self.register_pricing(p)

    def register_pricing(self, pricing: ModelPricing) -> None:
        self._pricing[(pricing.provider.lower(), pricing.model_id.lower())] = pricing

    def get_pricing(self, model_id: str, provider: str = "lapis") -> ModelPricing | None:
        key = (provider.lower(), model_id.lower())
        if key in self._pricing:
            return self._pricing[key]
        for (_prov, mod), pricing in self._pricing.items():
            if mod == model_id.lower():
                return pricing
        return None

    def calculate_cost(
        self,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str = "lapis",
    ) -> float:
        pricing = self.get_pricing(model_id, provider)
        if pricing is None:
            return 0.0
        return pricing.calculate_cost(prompt_tokens, completion_tokens)
