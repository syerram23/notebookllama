import pytest

from src.notebooklm_clone.models import (
    Notebook,
)
from src.notebooklm_clone.utils import MindMap
from src.notebooklm_clone.audio import MultiTurnConversation, ConversationTurn
from pydantic import ValidationError


def test_notebook() -> None:
    n1 = Notebook(
        summary="This is a summary",
        questions=[
            "What is the capital of Spain?",
            "What is the capital of France?",
            "What is the capital of Italy?",
            "What is the capital of Portugal?",
            "What is the capital of Germany?",
        ],
        answers=[
            "Madrid",
            "Paris",
            "Rome",
            "Lisbon",
            "Berlin",
        ],
        highlights=["This", "is", "a", "summary"],
    )
    assert n1.summary == "This is a summary"
    assert n1.questions[0] == "What is the capital of Spain?"
    assert n1.answers[0] == "Madrid"
    assert n1.highlights[0] == "This"
    # Fewer answers than questions
    with pytest.raises(ValidationError):
        Notebook(
            summary="This is a summary",
            questions=[
                "What is the capital of France?",
                "What is the capital of Italy?",
                "What is the capital of Portugal?",
                "What is the capital of Germany?",
            ],
            answers=[
                "Paris",
                "Rome",
                "Lisbon",
            ],
            highlights=["This", "is", "a", "summary"],
        )
    # Fewer highlights than required
    with pytest.raises(ValidationError):
        Notebook(
            summary="This is a summary",
            questions=[
                "What is the capital of Spain?",
                "What is the capital of France?",
                "What is the capital of Italy?",
                "What is the capital of Portugal?",
                "What is the capital of Germany?",
            ],
            answers=[
                "Madrid",
                "Paris",
                "Rome",
                "Lisbon",
                "Berlin",
            ],
            highlights=["This", "is"],
        )


def test_mind_map() -> None:
    m1 = MindMap(
        nodes=[
            ("A", "Auxin is released"),
            ("B", "Travels to the roots"),
            ("C", "Root cells grow in dimensions"),
        ],
        edges=[("A", "B"), ("A", "C"), ("B", "C")],
    )
    assert m1.nodes[0][0] == "A"
    assert m1.nodes[0][1] == "Auxin is released"
    assert m1.edges[0] == ("A", "B")
    with pytest.raises(ValidationError):
        MindMap(
            nodes=[
                ("A", "Auxin is released"),
                ("B", "Travels to the roots"),
                ("C", "Root cells grow in dimensions"),
            ],
            edges=[("A", "B"), ("A", "D"), ("B", "C")],
        )


def test_multi_turn_conversation() -> None:
    turns = [
        ConversationTurn(speaker="speaker1", content="Hello, who are you?"),
        ConversationTurn(speaker="speaker2", content="I am very well, how about you?"),
        ConversationTurn(speaker="speaker1", content="I am well too, thanks!"),
    ]
    assert turns[0].speaker == "speaker1"
    assert turns[0].content == "Hello, who are you?"
    conversation = MultiTurnConversation(
        conversation=turns,
    )
    assert isinstance(conversation.conversation, list)
    assert isinstance(conversation.conversation[0], ConversationTurn)
    wrong_turns = [
        ConversationTurn(speaker="speaker1", content="Hello, who are you?"),
        ConversationTurn(speaker="speaker2", content="I am very well, how about you?"),
    ]
    wrong_turns1 = [
        ConversationTurn(speaker="speaker2", content="Hello, who are you?"),
        ConversationTurn(speaker="speaker1", content="I am very well, how about you?"),
        ConversationTurn(speaker="speaker2", content="I am well too!"),
    ]
    wrong_turns2 = [
        ConversationTurn(speaker="speaker1", content="Hello, who are you?"),
        ConversationTurn(speaker="speaker1", content="How is your life going?"),
        ConversationTurn(
            speaker="speaker2",
            content="What is all this interest in me all of a sudden?!",
        ),
    ]
    wrong_turns3 = [
        ConversationTurn(speaker="speaker1", content="Hello, who are you?"),
        ConversationTurn(speaker="speaker2", content="I'm well! But..."),
        ConversationTurn(
            speaker="speaker2",
            content="...What is all this interest in me all of a sudden?!",
        ),
    ]
    with pytest.raises(ValidationError):
        MultiTurnConversation(conversation=wrong_turns)
    with pytest.raises(ValidationError):
        MultiTurnConversation(conversation=wrong_turns1)
    with pytest.raises(ValidationError):
        MultiTurnConversation(conversation=wrong_turns2)
    with pytest.raises(ValidationError):
        MultiTurnConversation(conversation=wrong_turns3)
