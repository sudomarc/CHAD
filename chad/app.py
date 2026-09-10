from __future__ import annotations

from dataclasses import dataclass

from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest, Conversation
from chad.llm.client import LLMError, LapisClient
from chad.storage.json_store import ConversationStore


@dataclass(slots=True)
class ChadApp:
    config: AppConfig
    client: LapisClient
    store: ConversationStore
    conversation: Conversation

    @classmethod
    def create(cls, config: AppConfig, client: LapisClient) -> "ChadApp":
        store = ConversationStore(config.storage_dir)
        conversation = Conversation(system_prompt=config.system_prompt, model=client.current_model().id)
        return cls(config=config, client=client, store=store, conversation=conversation)

    def new_conversation(self) -> Conversation:
        self.conversation = Conversation(
            system_prompt=self.config.system_prompt,
            model=self.client.current_model().id,
        )
        return self.conversation

    def request(self, text: str) -> ChatRequest:
        self.conversation.add_user(text)
        request = ChatRequest(
            messages=tuple(self.conversation.context()),
            model=self.conversation.model,
            temperature=self.config.generation.temperature,
            top_k=self.config.generation.top_k,
            top_p=self.config.generation.top_p,
            max_new_tokens=self.config.generation.max_new_tokens,
        )
        request.validate()
        return request

    def send(self, text: str) -> str:
        request = self.request(text)
        try:
            response = self.client.generate(request)
        except LLMError:
            self.conversation.messages.pop()
            raise
        self.conversation.add_assistant(response)
        self.store.save(self.conversation)
        return response

    def history(self) -> list[Conversation]:
        return self.store.list()

    def load_conversation(self, conversation_id: str) -> Conversation:
        self.conversation = self.store.load(conversation_id)
        return self.conversation
