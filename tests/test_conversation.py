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


def test_conversation_summary() -> None:
    conv = Conversation()
    assert conv.summary is None

    conv.set_summary("User is asking about Python typing.")
    assert conv.summary == "User is asking about Python typing."

    data = conv.to_dict()
    assert data["summary"] == "User is asking about Python typing."

    restored = Conversation.from_dict(data)
    assert restored.summary == "User is asking about Python typing."


def test_conversation_correlation_and_idempotency() -> None:
    conv = Conversation()

    m1 = conv.add_user("First question", correlation_id="req-1", idempotency_key="key-1")
    assert m1.correlation_id == "req-1"
    assert m1.idempotency_key == "key-1"
    assert "key-1" in conv.processed_idempotency_keys

    # Resubmitting identical idempotency key returns existing message without duplication
    m1_dup = conv.add_user("First question duplicated", correlation_id="req-1", idempotency_key="key-1")
    assert m1_dup == m1
    assert len(conv.messages) == 1

    m2 = conv.add_assistant("First answer", correlation_id="req-1", idempotency_key="resp-key-1")
    assert m2.correlation_id == "req-1"
    assert m2.idempotency_key == "resp-key-1"

    data = conv.to_dict()
    assert data["processed_idempotency_keys"] == ["key-1", "resp-key-1"]

    restored = Conversation.from_dict(data)
    assert restored.processed_idempotency_keys == ["key-1", "resp-key-1"]


def test_chad_app_idempotency_and_correlation(tmp_path: pytest.TempPathFactory) -> None:
    from pathlib import Path

    from chad.app import ChadApp
    from chad.core.config import AppConfig
    from chad.core.conversation import ChatRequest
    from chad.llm.client import LapisClient, ModelInfo

    class CallCounterClient(LapisClient):
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, request: ChatRequest) -> str:
            self.calls += 1
            return f"Response #{self.calls} for {request.messages[-1].content}"

        def current_model(self) -> ModelInfo:
            return ModelInfo(id="counter-model", display_name="Counter Model")

    client = CallCounterClient()
    config = AppConfig(storage_dir=Path(tmp_path) / "storage")
    app = ChadApp.create(config, client)

    resp1 = app.send("Hello", correlation_id="corr-99", idempotency_key="req-99")
    assert resp1 == "Response #1 for Hello"
    assert client.calls == 1

    # Second call with same idempotency key returns cached answer and does not invoke gateway
    resp2 = app.send("Hello", correlation_id="corr-99", idempotency_key="req-99")
    assert resp2 == "Response #1 for Hello"
    assert client.calls == 1
