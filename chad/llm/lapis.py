from __future__ import annotations

from pathlib import Path
import time

from chad.core.conversation import ChatRequest
from chad.llm.client import LapisClient, ModelInfo
from chad.llm.gateway import (
    GenerationError,
    ModelCapabilities,
    ModelResponse,
    ModelUnavailableError,
)

_ROLE_LABELS = {
    "system": "System",
    "user": "User",
    "assistant": "Assistant",
}


class LocalLapisClient(LapisClient):
    """Adapter for the public LapisLLM inference facade.

    CHAD deliberately depends on Lapis' inference/user API rather than model,
    tokenizer, checkpoint, or sampling internals.
    """

    def __init__(self, checkpoint: str | Path, device: str = "auto") -> None:
        try:
            from lapis.inference.runtime import LapisRuntime, SamplingConfig
        except ImportError as exc:
            raise ModelUnavailableError(
                "LapisLLM is not installed. Install the Lapis runtime before starting CHAD."
            ) from exc

        path = Path(checkpoint)
        if not path.is_file():
            raise ModelUnavailableError(f"Lapis checkpoint was not found: {path}")

        try:
            self._runtime = LapisRuntime.from_checkpoint(path, device)
        except Exception as exc:  # Lapis exposes several concrete load errors.
            raise ModelUnavailableError("The selected Lapis model could not be loaded.") from exc

        self._sampling_type = SamplingConfig
        context_len = getattr(self._runtime.model, "max_position_embeddings", None)
        capabilities = ModelCapabilities(
            text_generation=True,
            streaming=False,
            context_length=context_len,
        )

        self._model = ModelInfo(
            id=path.stem,
            display_name=f"Lapis — {path.stem}",
            context_length=context_len,
            backend="lapis_local",
            capabilities=capabilities,
        )

    def _prompt(self, request: ChatRequest) -> str:
        request.validate()
        parts: list[str] = []
        for message in request.messages:
            parts.append(f"{_ROLE_LABELS[message.role.value]}:\n{message.content}")
        parts.append("Assistant:")
        return "\n\n".join(parts)

    def generate_response(self, request: ChatRequest) -> ModelResponse:
        prompt = self._prompt(request)
        start_time = time.perf_counter()
        try:
            sampling = self._sampling_type(
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
                top_k=request.top_k,
                top_p=request.top_p,
            )
            result = self._runtime.generate(prompt, sampling)
        except (ValueError, RuntimeError) as exc:
            raise GenerationError("Lapis could not generate a response.") from exc

        latency_ms = (time.perf_counter() - start_time) * 1000
        result = result.removeprefix(prompt).strip()
        return ModelResponse(
            content=result,
            model_id=self._model.id,
            provider="lapis_local",
            latency_ms=latency_ms,
        )

    def generate(self, request: ChatRequest) -> str:
        return self.generate_response(request).content

    def current_model(self) -> ModelInfo:
        return self._model
