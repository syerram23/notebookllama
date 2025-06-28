import pytest

from elevenlabs import AsyncElevenLabs
from src.notebooklm_clone.audio import PodcastGenerator
from src.notebooklm_clone.models import MultiTurnConversation
from llama_index.core.llms.structured_llm import StructuredLLM
from llama_index.core.llms import MockLLM
from pydantic import BaseModel, ValidationError


class MockElevenLabs(AsyncElevenLabs):
    def __init__(self, test_api_key: str) -> None:
        self.test_api_key = test_api_key


class TestModel(BaseModel):
    test: str


@pytest.fixture()
def correct_structured_llm() -> StructuredLLM:
    return MockLLM().as_structured_llm(MultiTurnConversation)


@pytest.fixture()
def wrong_structured_llm() -> StructuredLLM:
    return MockLLM().as_structured_llm(TestModel)


def test_podcast_generator_model(
    correct_structured_llm: StructuredLLM, wrong_structured_llm: StructuredLLM
) -> None:
    n = PodcastGenerator(
        client=MockElevenLabs(test_api_key="a"), llm=correct_structured_llm
    )
    assert isinstance(n.client, AsyncElevenLabs)
    assert isinstance(n.llm, StructuredLLM)
    assert n.llm.output_cls == MultiTurnConversation
    with pytest.raises(ValidationError):
        PodcastGenerator(
            client=MockElevenLabs(test_api_key="a"), llm=wrong_structured_llm
        )
