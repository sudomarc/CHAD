import pytest

from chad.core.conversation import Conversation
from chad.core.messages import MessageRole


def test_conversation_preserves_multi_turn_order() -> None:
    conversation = Conversation(system_prompt="Be concise.", model="latest")
    conversation.add_user("My name is Marco.")
    conversation.add_assistant("Understood.")
    conversation.add_user("What is my name?")

    context = conversation.context()

    assert [message.role for message in context] == [
        MessageRole.SYSTEM,
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
    ]
    assert context[-1].content == "What is my name?"



def test_context_rejects_non_positive_message_limit() -> None:
    conversation = Conversation()
    with pytest.raises(ValueError, match="max_messages"):
        conversation.context(max_messages=0)


def test_chat_request_rejects_non_finite_sampling_values() -> None:
    import math

    from chad.core.conversation import ChatRequest
    from chad.core.messages import Message

    request = ChatRequest(
        messages=(Message(MessageRole.USER, "hello"),),
        temperature=math.inf,
    )
    with pytest.raises(ValueError, match="finite"):
        request.validate()
