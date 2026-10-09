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


def test_conversation_branching_editing_and_regeneration() -> None:
    conv = Conversation()
    m1 = conv.add_user("First question")
    m2 = conv.add_assistant("First answer")

    assert m1.parent_id is None
    assert m2.parent_id == m1.id
    assert conv.get_active_messages() == [m1, m2]

    # Edit m1
    m1_edit = conv.edit_message(m1.id, "Edited first question")
    assert m1_edit.parent_id is None
    assert m1_edit.edited_from_id == m1.id
    assert conv.get_active_messages() == [m1_edit]

    # Add response on new branch
    m3 = conv.add_assistant("Response to edited question")
    assert m3.parent_id == m1_edit.id
    assert conv.get_active_messages() == [m1_edit, m3]

    # Switch back to old branch
    conv.switch_branch(m2.id)
    assert conv.get_active_messages() == [m1, m2]

    # Test regeneration
    user_target = conv.regenerate_message(m2.id)
    assert user_target == m1
    assert conv.get_active_messages() == [m1]


def test_conversation_lifecycle_states() -> None:
    from chad.core.conversation import ConversationStatus

    conv = Conversation()
    assert conv.status == ConversationStatus.ACTIVE

    conv.archive()
    assert conv.status == ConversationStatus.ARCHIVED

    conv.unarchive()
    assert conv.status == ConversationStatus.ACTIVE

    conv.soft_delete()
    assert conv.status == ConversationStatus.DELETED

    conv.restore()
    assert conv.status == ConversationStatus.ACTIVE


def test_conversation_idempotency_and_correlation_id() -> None:
    conv = Conversation()
    m1 = conv.add_user("Hello", correlation_id="req-1", idempotency_key="key-1")
    assert m1.correlation_id == "req-1"
    assert m1.idempotency_key == "key-1"

    # Duplicate call with same idempotency key should return existing message
    m1_dup = conv.add_user("Hello again", correlation_id="req-2", idempotency_key="key-1")
    assert m1_dup is m1
    assert len(conv.messages) == 1

    m2 = conv.add_assistant("Hi there", correlation_id="req-1", idempotency_key="key-2")
    assert m2.correlation_id == "req-1"
    assert m2.idempotency_key == "key-2"

    m2_dup = conv.add_assistant("Hi duplicate", idempotency_key="key-2")
    assert m2_dup is m2
    assert len(conv.messages) == 2


def test_conversation_summary_and_serialization() -> None:
    conv = Conversation(title="Summary test")
    conv.record_summary("User said hello and assistant greeted back.")
    assert conv.summary == "User said hello and assistant greeted back."

    conv.add_user("Message 1", correlation_id="corr-1", idempotency_key="idem-1")
    conv.add_assistant("Message 2", correlation_id="corr-1", idempotency_key="idem-2")

    data = conv.to_dict()
    assert data["summary"] == "User said hello and assistant greeted back."

    restored = Conversation.from_dict(data)
    assert restored.summary == "User said hello and assistant greeted back."
    assert restored.messages[0].correlation_id == "corr-1"
    assert restored.messages[0].idempotency_key == "idem-1"
    assert restored.messages[1].correlation_id == "corr-1"
    assert restored.messages[1].idempotency_key == "idem-2"
