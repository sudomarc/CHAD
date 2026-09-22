from __future__ import annotations

from dataclasses import dataclass, field

from chad.core.config import AppConfig
from chad.core.context import ContextLimitError
from chad.core.conversation import ChatRequest, Conversation
from chad.llm.client import LapisClient, LLMError
from chad.llm.gateway import ModelGateway
from chad.storage.json_store import ConversationStore


@dataclass(slots=True)
class ChadApp:
    config: AppConfig
    client: LapisClient
    store: ConversationStore
    conversation: Conversation
    gateway: ModelGateway = field(init=False)

    def __post_init__(self) -> None:
        if isinstance(self.client, ModelGateway):
            self.gateway = self.client
        else:
            self.gateway = ModelGateway(default_client=self.client)

    @classmethod
    def create(
        cls,
        config: AppConfig,
        client: LapisClient | ModelGateway,
    ) -> ChadApp:
        config.validate()
        store = ConversationStore(config.storage_dir)

        if isinstance(client, ModelGateway):
            gateway = client
            model_info = gateway.get_model(gateway.list_models()[0].id)
            client_ref = client
        else:
            gateway = ModelGateway(default_client=client)
            model_info = client.current_model()
            client_ref = client

        conversation = Conversation(
            system_prompt=config.system_prompt,
            model=model_info.id,
        )
        app_instance = cls(
            config=config,
            client=client_ref,
            store=store,
            conversation=conversation,
        )
        app_instance.gateway = gateway
        return app_instance

    def new_conversation(self) -> Conversation:
        model_id = self.gateway.list_models()[0].id if self.gateway.list_models() else self.client.current_model().id
        self.conversation = Conversation(
            system_prompt=self.config.system_prompt,
            model=model_id,
        )
        return self.conversation

    def request(self, text: str) -> ChatRequest:
        self.conversation.add_user(text)
        max_input_tokens = self.config.max_context_tokens
        if max_input_tokens is None:
            model_id = self.conversation.model
            capabilities = self.gateway.capabilities(model_id)
            context_length = capabilities.context_length
            if context_length is not None:
                max_input_tokens = context_length - self.config.generation.max_new_tokens
                if max_input_tokens < 1:
                    raise ContextLimitError(
                        "generation settings leave no room for conversation context"
                    )

        request = ChatRequest(
            messages=tuple(
                self.conversation.context(
                    max_messages=self.config.max_context_messages,
                    max_input_tokens=max_input_tokens,
                )
            ),
            model=self.conversation.model,
            temperature=self.config.generation.temperature,
            top_k=self.config.generation.top_k,
            top_p=self.config.generation.top_p,
            max_new_tokens=self.config.generation.max_new_tokens,
        )
        request.validate()
        return request

    def send(self, text: str) -> str:
        try:
            request = self.request(text)
            response = self.gateway.generate(request)
            content = response.content
        except (LLMError, ContextLimitError):
            if self.conversation.messages and self.conversation.messages[-1].role.value == "user":
                self.conversation.messages.pop()
            raise
        self.conversation.add_assistant(content)
        self.store.save(self.conversation)
        return content

    def history(self) -> list[Conversation]:
        return self.store.list()

    def load_conversation(self, conversation_id: str) -> Conversation:
        self.conversation = self.store.load(conversation_id)
        return self.conversation
