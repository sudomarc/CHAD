from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from chad.core.messages import Message


class ContextLimitError(ValueError):
    """Raised when the newest request cannot fit in the configured context budget."""


def estimate_tokens(text: str, chars_per_token: int = 4) -> int:
    if chars_per_token < 1:
        raise ValueError("chars_per_token must be at least 1")
    return max(1, math.ceil(len(text) / chars_per_token))


def estimate_message_tokens(message: Message, chars_per_token: int = 4) -> int:
    return estimate_tokens(message.content, chars_per_token)


@dataclass(frozen=True, slots=True)
class ContextBudget:
    max_input_tokens: int
    chars_per_token: int = 4

    def validate(self) -> None:
        if self.max_input_tokens < 1:
            raise ValueError("max_input_tokens must be at least 1")
        if self.chars_per_token < 1:
            raise ValueError("chars_per_token must be at least 1")

    def estimate(self, messages: Sequence[Message]) -> int:
        self.validate()
        return sum(
            estimate_message_tokens(message, self.chars_per_token)
            for message in messages
        )

    def trim(self, messages: Sequence[Message]) -> list[Message]:
        self.validate()
        selected = list(messages)
        system_messages = [message for message in selected if message.role.value == "system"]
        history = [message for message in selected if message.role.value != "system"]

        while system_messages and self.estimate([*system_messages, *history]) > self.max_input_tokens:
            if len(system_messages) + sum(
                estimate_message_tokens(message, self.chars_per_token)
                for message in history
            ) <= self.max_input_tokens:
                break
            history.pop(0)
            if not history:
                break

        candidate = [*system_messages, *history]
        while candidate and self.estimate(candidate) > self.max_input_tokens and len(candidate) > 1:
            if candidate[0].role.value == "system":
                candidate.pop(1)
            else:
                candidate.pop(0)

        if not candidate or self.estimate(candidate) > self.max_input_tokens:
            raise ContextLimitError("latest conversation context exceeds the input token budget")
        return candidate
