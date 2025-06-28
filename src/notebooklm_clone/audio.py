import tempfile as temp
import os
import uuid
from dotenv import load_dotenv

from pydub import AudioSegment
from elevenlabs import AsyncElevenLabs
from llama_index.core.llms.structured_llm import StructuredLLM
from typing_extensions import Self
from typing import List, Literal
from pydantic import BaseModel, ConfigDict, model_validator, Field
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAIResponses


class ConversationTurn(BaseModel):
    speaker: Literal["speaker1", "speaker2"] = Field(
        description="The person who is speaking",
    )
    content: str = Field(
        description="The content of the speech",
    )


class MultiTurnConversation(BaseModel):
    conversation: List[ConversationTurn] = Field(
        description="List of conversation turns. Conversation must start with speaker1, and continue with an alternance of speaker1 and speaker2",
        min_length=3,
        max_length=50,
        examples=[
            [
                ConversationTurn(speaker="speaker1", content="Hello, who are you?"),
                ConversationTurn(
                    speaker="speaker2", content="I am very well, how about you?"
                ),
                ConversationTurn(speaker="speaker1", content="I am well too, thanks!"),
            ]
        ],
    )

    @model_validator(mode="after")
    def validate_conversation(self) -> Self:
        speakers = [turn.speaker for turn in self.conversation]
        if speakers[0] != "speaker1":
            raise ValueError("Conversation must start with speaker1")
        for i, speaker in enumerate(speakers):
            if i % 2 == 0 and speaker != "speaker1":
                raise ValueError(
                    "Conversation must be an alternance between speaker1 and speaker2"
                )
            elif i % 2 != 0 and speaker != "speaker2":
                raise ValueError(
                    "Conversation must be an alternance between speaker1 and speaker2"
                )
            continue
        return self


class PodcastGenerator(BaseModel):
    llm: StructuredLLM
    client: AsyncElevenLabs

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def validate_podcast(self) -> Self:
        try:
            assert self.llm.output_cls == MultiTurnConversation
        except AssertionError:
            raise ValueError(
                f"The output class of the structured LLM must be {MultiTurnConversation.__qualname__}, your LLM has output class: {self.llm.output_cls.__qualname__}"
            )
        return self

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

    async def _conversation_audio(self, conversation: MultiTurnConversation) -> str:
        files: List[str] = []
        for turn in conversation.conversation:
            if turn.speaker == "speaker1":
                speech_iterator = self.client.text_to_speech.convert(
                    voice_id="nPczCjzI2devNBz1zQrb",
                    text=turn.content,
                    output_format="mp3_22050_32",
                    model_id="eleven_turbo_v2_5",
                )
            else:
                speech_iterator = self.client.text_to_speech.convert(
                    voice_id="Xb7hH8MSUJpSbSDYk0k2",
                    text=turn.content,
                    output_format="mp3_22050_32",
                    model_id="eleven_turbo_v2_5",
                )
            fl = temp.NamedTemporaryFile(
                suffix=".mp3", delete=False, delete_on_close=False
            )
            with open(fl.name, "wb") as f:
                async for chunk in speech_iterator:
                    if chunk:
                        f.write(chunk)
            files.append(fl.name)

        output_path = f"conversation_{str(uuid.uuid4())}.mp3"
        combined_audio: AudioSegment = AudioSegment.empty()

        for file_path in files:
            audio = AudioSegment.from_file(file_path)
            combined_audio += audio

            # Export with high quality MP3 settings
            combined_audio.export(
                output_path,
                format="mp3",
                bitrate="320k",  # High quality bitrate
                parameters=["-q:a", "0"],  # Highest quality
            )
            os.remove(file_path)

        return output_path

    async def create_conversation(self, file_transcript: str):
        conversation = await self._conversation_script(file_transcript=file_transcript)
        podcast_file = await self._conversation_audio(conversation=conversation)
        return podcast_file


load_dotenv()

if os.getenv("ELEVENLABS_API_KEY", None) and os.getenv("OPENAI_API_KEY", None):
    SLLM = OpenAIResponses(
        model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY")
    ).as_structured_llm(MultiTurnConversation)
    EL_CLIENT = AsyncElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    PODCAST_GEN = PodcastGenerator(llm=SLLM, client=EL_CLIENT)
