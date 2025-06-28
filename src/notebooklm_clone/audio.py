from elevenlabs import AsyncElevenLabs
from llama_index.core.llms.structured_llm import StructuredLLM
from models import MultiTurnConversation
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, model_validator
from llama_index.core.llms import ChatMessage


class PodcastGenerator(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)
    llm: StructuredLLM
    client: AsyncElevenLabs

    def __init__(self, client: AsyncElevenLabs, llm: StructuredLLM) -> None:
        self.client = client
        self.llm = llm

    @model_validator(mode="after")
    def validate_podcast(self) -> Self:
        try:
            assert self.llm.output_cls == MultiTurnConversation
        except AssertionError:
            raise ValueError(
                f"The output class of the structured LLM must be {MultiTurnConversation.__qualname__}, your LLM has output class: {self.llm.output_cls.__qualname__}"
            )

    async def _conversation_script(self, file_transcript: str) -> MultiTurnConversation:
        response = await self.llm.achat(
            messages=[
                ChatMessage(
                    role="user",
                    content=f"Please create a multi-turn conversation with two speakers starting from this file transcript:\n\n'''\n{file_transcript}\n'''",
                )
            ]
        )
        return MultiTurnConversation.model_validate_json(response.message.content)

    async def _conversation_audio(
        self, conversation: MultiTurnConversation
    ) -> bytes: ...

    async def create_conversation(self, file_transcript: str):
        conversation = self._conversation_script(file_transcript=file_transcript)
        podcast = self._conversation_audio(conversation=conversation)
        return podcast
