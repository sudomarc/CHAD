from datetime import UTC, datetime

from chad.core.messages import Message, MessageRole


def test_message_round_trip_preserves_identity_and_timestamp() -> None:
    created_at = datetime.now(UTC).isoformat()
    message = Message(MessageRole.USER, "hello", id="message-1", created_at=created_at)

    restored = Message.from_dict(message.to_dict())

    assert restored.id == "message-1"
    assert restored.created_at == created_at
    assert restored.role is MessageRole.USER
    assert restored.content == "hello"


def test_message_rejects_blank_content_and_id() -> None:
    try:
        Message(MessageRole.USER, "   ")
    except ValueError:
        pass
    else:
        raise AssertionError("blank message content should be rejected")

    try:
        Message(MessageRole.USER, "hello", id=" ")
    except ValueError:
        pass
    else:
        raise AssertionError("blank message id should be rejected")
