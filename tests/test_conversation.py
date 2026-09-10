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
