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


def test_store_handles_status_filtering_and_deletion(tmp_path) -> None:
    from chad.core.conversation import ConversationStatus

    store = ConversationStore(tmp_path / "conversations")

    c1 = Conversation(title="Active 1")
    c1.add_user("Hi")

    c2 = Conversation(title="Archived 1")
    c2.archive()

    c3 = Conversation(title="Deleted 1")
    c3.soft_delete()

    store.save(c1)
    store.save(c2)
    store.save(c3)

    active_list = store.list(status=ConversationStatus.ACTIVE)
    assert len(active_list) == 1
    assert active_list[0].id == c1.id

    archived_list = store.list(status=ConversationStatus.ARCHIVED)
    assert len(archived_list) == 1
    assert archived_list[0].id == c2.id

    store.delete(c1.id, hard=False)
    soft_deleted = store.load(c1.id)
    assert soft_deleted.status == ConversationStatus.DELETED

    store.delete(c2.id, hard=True)
    import pytest
    with pytest.raises(KeyError):
        store.load(c2.id)
