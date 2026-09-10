from __future__ import annotations

from chad.app import ChadApp
from chad.commands import CommandRouter
from chad.llm.client import LLMError


def run_cli(app: ChadApp) -> None:
    commands = CommandRouter()
    model = app.client.current_model()
    print(f"CHAD — {model.display_name}")
    print("Type a message to chat, or /help for controls.\n")

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        if not text:
            continue

        result = commands.dispatch(text)
        if result.handled:
            if result.output == "__NEW__":
                app.new_conversation()
                print("Started a new conversation.")
            elif result.output == "__CLEAR__":
                print("\033[2J\033[H", end="")
            elif result.output:
                print(result.output)
            if result.should_exit:
                print("Goodbye.")
                return
            continue

        try:
            response = app.send(text)
        except LLMError as exc:
            print(f"\nCHAD couldn't generate a response.\nReason: {exc}\n")
            continue
        except Exception:
            if app.config.developer_mode:
                raise
            print("\nCHAD couldn't generate a response. Technical details are available in developer logs.\n")
            continue

        print(f"\nCHAD: {response}\n")
