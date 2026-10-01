import json

from chad.memory.engine import MemoryEngine
from chad.memory.models import MemoryConflict, MemoryItem, MemoryScope, MemoryType
from chad.memory.store import MemoryStore


def test_memory_item_serialization():
    item = MemoryItem(
        key="language_pref",
        content="French",
        memory_type=MemoryType.USER,
        scope=MemoryScope.USER,
        user_id="user_123",
    )
    data = item.to_dict()
    assert data["key"] == "language_pref"
    assert data["content"] == "French"
    assert data["memory_type"] == "user"
    assert data["scope"] == "user"
    assert data["user_id"] == "user_123"

    deserialized = MemoryItem.from_dict(data)
    assert deserialized.key == item.key
    assert deserialized.content == item.content
    assert deserialized.memory_type == MemoryType.USER
    assert deserialized.scope == MemoryScope.USER
    assert deserialized.user_id == "user_123"


def test_memory_store_crud():
    store = MemoryStore()
    item1 = MemoryItem(
        key="k1", content="c1", memory_type=MemoryType.WORKING, scope=MemoryScope.SESSION, session_id="s1"
    )
    item2 = MemoryItem(
        key="k2", content="c2", memory_type=MemoryType.USER, scope=MemoryScope.USER, user_id="u1"
    )

    store.add(item1)
    store.add(item2)

    assert store.get(item1.id) == item1
    assert store.get_by_key("k1") == item1
    assert len(store.list()) == 2
    assert len(store.list(memory_type=MemoryType.USER)) == 1

    updated = store.update(item1.id, content="updated_c1")
    assert updated is not None
    assert updated.content == "updated_c1"

    deleted = store.delete(item1.id)
    assert deleted is True
    assert store.get(item1.id) is None
    assert len(store.list()) == 1


def test_memory_store_clear_and_export():
    store = MemoryStore()
    item1 = MemoryItem(
        key="k1", content="c1", memory_type=MemoryType.WORKING, scope=MemoryScope.SESSION, session_id="s1"
    )
    item2 = MemoryItem(
        key="k2", content="c2", memory_type=MemoryType.USER, scope=MemoryScope.USER, user_id="u1"
    )
    store.add(item1)
    store.add(item2)

    exported = store.export_json(scope=MemoryScope.USER)
    data = json.loads(exported)
    assert len(data) == 1
    assert data[0]["key"] == "k2"

    new_store = MemoryStore()
    imported = new_store.import_json(exported)
    assert len(imported) == 1
    assert imported[0].key == "k2"

    cleared = store.clear_scope(MemoryScope.SESSION)
    assert cleared == 1
    assert len(store.list()) == 1


def test_memory_engine_user_preference_and_conflict():
    engine = MemoryEngine()

    item1, conflict1 = engine.add_user_preference("tone", "concise", user_id="u123")
    assert item1.content == "concise"
    assert conflict1 is None

    # Updating preference triggers a conflict notification
    item2, conflict2 = engine.add_user_preference("tone", "detailed", user_id="u123")
    assert item2.id == item1.id
    assert item2.content == "detailed"
    assert conflict2 is not None
    assert isinstance(conflict2, MemoryConflict)
    assert conflict2.conflict_type == "update"
    assert "concise" in conflict2.reason
    assert "detailed" in conflict2.reason


def test_memory_engine_conversation_summary():
    engine = MemoryEngine()
    summary_item = engine.record_conversation_summary(
        session_id="sess_1",
        summary="User discussed Python async patterns.",
        message_count=10,
    )
    assert summary_item.key == "summary:sess_1"
    assert summary_item.content == "User discussed Python async patterns."
    assert summary_item.metadata["message_count"] == 10

    # Update summary
    updated_item = engine.record_conversation_summary(
        session_id="sess_1",
        summary="User discussed Python async patterns and memory safety.",
        message_count=15,
    )
    assert updated_item.id == summary_item.id
    assert updated_item.metadata["message_count"] == 15


def test_memory_engine_search():
    engine = MemoryEngine()
    engine.add_working_memory("current_task", "Refactor the memory module in Python", session_id="s1")
    engine.add_user_preference("framework", "Prefers Pytest over Unittest", user_id="u1")
    engine.add_project_memory("backend", "PostgreSQL vector store", project_id="p1")

    results = engine.search_memories("Python memory module", session_id="s1")
    assert len(results) > 0
    top_item, score = results[0]
    assert top_item.key == "current_task"
    assert score > 0
