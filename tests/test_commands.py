from chad.commands import CommandRouter


def test_natural_language_is_not_a_command() -> None:
    result = CommandRouter().dispatch("Explain transformers")
    assert result.handled is False


def test_explicit_command_is_handled() -> None:
    result = CommandRouter().dispatch("/help")
    assert result.handled is True
    assert "Everything else" in (result.output or "")
