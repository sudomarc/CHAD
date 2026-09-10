from __future__ import annotations

from pathlib import Path

from chad.core.conversation import ChatRequest
from chad.llm.client import GenerationError, LapisClient, ModelInfo, ModelUnavailableError

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
        self._model = ModelInfo(
            id=path.stem,
            display_name=f"Lapis — {path.stem}",
            context_length=getattr(self._runtime.model, "max_position_embeddings", None),
        )

    def _prompt(self, request: ChatRequest) -> str:
        request.validate()
        parts: list[str] = []
        for message in request.messages:
            parts.append(f"{_ROLE_LABELS[message.role.value]}:\n{message.content}")
        parts.append("Assistant:")
        return "\n\n".join(parts)

    def generate(self, request: ChatRequest) -> str:
        prompt = self._prompt(request)
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

        # Current LapisRuntime returns the decoded prompt plus generated text.
        # Strip only the exact prompt when present; never mutate arbitrary output.
        result = result.removeprefix(prompt)
        return result.strip()

    def current_model(self) -> ModelInfo:
        return self._model
