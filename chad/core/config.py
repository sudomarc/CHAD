from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    temperature: float = 0.8
    top_k: int = 40
    top_p: float = 0.95
    max_new_tokens: int = 128

    def validate(self) -> None:
        values = (self.temperature, self.top_p)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("generation settings must be finite")
        if self.temperature <= 0:
            raise ValueError("temperature must be greater than 0")
        if self.top_k < 0:
            raise ValueError("top_k must be >= 0")
        if not 0 < self.top_p <= 1:
            raise ValueError("top_p must be in the range (0, 1]")
        if self.max_new_tokens < 1:
            raise ValueError("max_new_tokens must be at least 1")


@dataclass(frozen=True, slots=True)
class LapisSettings:
    base_url: str = "http://127.0.0.1:8000"
    model: str | None = None
    checkpoint: Path = Path("checkpoints/latest.pt")
    device: str = "auto"


@dataclass(frozen=True, slots=True)
class AppConfig:
    lapis: LapisSettings = LapisSettings()
    generation: GenerationSettings = GenerationSettings()
    storage_dir: Path = Path.home() / ".chad" / "conversations"
    system_prompt: str | None = None
    developer_mode: bool = False

    @classmethod
    def from_env(cls) -> AppConfig:
        lapis_url = os.getenv("CHAD_LAPIS_URL", "http://127.0.0.1:8000").rstrip("/")
        lapis_model = os.getenv("CHAD_LAPIS_MODEL") or None
        checkpoint = Path(os.getenv("CHAD_LAPIS_CHECKPOINT", "checkpoints/latest.pt"))
        device = os.getenv("CHAD_LAPIS_DEVICE", "auto")
        storage = Path(os.getenv("CHAD_STORAGE_DIR", str(Path.home() / ".chad" / "conversations")))
        developer = os.getenv("CHAD_DEVELOPER_MODE", "0").lower() in {"1", "true", "yes", "on"}
        settings = GenerationSettings(
            temperature=float(os.getenv("CHAD_TEMPERATURE", "0.8")),
            top_k=int(os.getenv("CHAD_TOP_K", "40")),
            top_p=float(os.getenv("CHAD_TOP_P", "0.95")),
            max_new_tokens=int(os.getenv("CHAD_MAX_NEW_TOKENS", "128")),
        )
        settings.validate()
        return cls(
            lapis=LapisSettings(
                base_url=lapis_url,
                model=lapis_model,
                checkpoint=checkpoint,
                device=device,
            ),
            generation=settings,
            storage_dir=storage,
            system_prompt=os.getenv("CHAD_SYSTEM_PROMPT") or None,
            developer_mode=developer,
        )
