import tempfile as temp
import os
import uuid

from pydub import AudioSegment
from elevenlabs import AsyncElevenLabs
from llama_index.core.llms.structured_llm import StructuredLLM
from src.notebooklm_clone.models import MultiTurnConversation
from typing_extensions import Self
from typing import List
from pydantic import BaseModel, ConfigDict, model_validator
from llama_index.core.llms import ChatMessage


class PodcastGenerator(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)
    llm: StructuredLLM
    client: AsyncElevenLabs

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
        conversation = self._conversation_script(file_transcript=file_transcript)
        podcast_file = self._conversation_audio(conversation=conversation)
        return podcast_file
