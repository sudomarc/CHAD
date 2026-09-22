from chad.core.conversation import Conversation
from chad.storage.json_store import ConversationStore


def test_store_round_trip_preserves_conversation_metadata(tmp_path) -> None:
    store = ConversationStore(tmp_path / "conversations")
    conversation = Conversation(title="Test", model="lapis-tiny")
    first = conversation.add_user("hello")
    conversation.add_assistant("hi")

    store.save(conversation)
    restored = store.load(conversation.id)

    assert restored.id == conversation.id
    assert restored.created_at == conversation.created_at
    assert restored.updated_at == conversation.updated_at
    assert restored.messages[0].id == first.id
    assert restored.messages[1].content == "hi"


def test_store_rejects_unsafe_conversation_ids(tmp_path) -> None:
    store = ConversationStore(tmp_path)

    for conversation_id in ("../escape", "a/b", "", "   "):
        try:
            store.load(conversation_id)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe id accepted: {conversation_id!r}")
