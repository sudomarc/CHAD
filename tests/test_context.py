import pytest

from chad.core.context import ContextBudget, ContextLimitError, estimate_tokens
from chad.core.messages import Message, MessageRole


def test_context_budget_trims_oldest_history_and_preserves_system_and_latest() -> None:
    messages = [
        Message(MessageRole.SYSTEM, "sys"),
        Message(MessageRole.USER, "old"),
        Message(MessageRole.ASSISTANT, "older-answer"),
        Message(MessageRole.USER, "latest"),
    ]

    budget = ContextBudget(max_input_tokens=9, chars_per_token=1)
    trimmed = budget.trim(messages)

    assert [message.content for message in trimmed] == ["sys", "latest"]
    assert budget.estimate(trimmed) == 9


def test_context_budget_rejects_context_when_latest_message_cannot_fit() -> None:
    messages = [
        Message(MessageRole.SYSTEM, "system"),
        Message(MessageRole.USER, "this message is too long"),
    ]

    with pytest.raises(ContextLimitError):
        ContextBudget(max_input_tokens=5, chars_per_token=1).trim(messages)


def test_estimate_tokens_is_deterministic_and_validates_ratio() -> None:
    assert estimate_tokens("abcdefgh", chars_per_token=4) == 2

    with pytest.raises(ValueError):
        estimate_tokens("hello", chars_per_token=0)
