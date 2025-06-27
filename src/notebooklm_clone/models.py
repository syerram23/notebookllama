from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Literal, Tuple
from typing_extensions import Self


class Notebook(BaseModel):
    summary: str = Field(
        description="Summary of the document.",
    )
    highlights: List[str] = Field(
        description="Highlights of the documents: 3 to 10 bullet points that represent the crucial knots of the documents.",
        min_length=3,
        max_length=10,
    )
    questions_and_answers: List[Dict[Literal["question", "answer"], str]] = Field(
        description="5 to 15 questions and answers about a given topic. This field should be organized as a list of dictionaries, each containing a 'question' and an 'answer' fields.",
        examples=[
            [
                {"question": "What is the capital of Spain?", "answer": "Madrid"},
                {"question": "What is the capital of France?", "answer": "Paris"},
                {"question": "What is the capital of Italy?", "answer": "Rome"},
                {"question": "What is the capital of Portugal?", "answer": "Lisbon"},
                {"question": "What is the capital of Germany?", "answer": "Berlin"},
            ]
        ],
        min_length=5,
        max_length=15,
    )


class MindMap(BaseModel):
    nodes: List[Tuple[str, str]] = Field(
        description="List of nodes of the mind map, with their ID as first element and their content as second. Content should never exceed 5 words.",
        examples=[
            [
                ("A", "Fall of the Roman Empire"),
                ("B", "476 AD"),
                ("C", "Barbarian invasions"),
            ],
            [
                ("A", "Auxin is released"),
                ("B", "Travels to the roots"),
                ("C", "Root cells grow in dimensions"),
            ],
        ],
    )
    edges: List[Tuple[str, str]] = Field(
        description="The edges connecting the nodes of the mind map, as a list of tuples containing the IDs of the two connected edges.",
        examples=[
            [("A", "B"), ("A", "C"), ("B", "C")],
            [("C", "A"), ("B", "C"), ("A", "B")],
        ],
    )

    @model_validator(mode="after")
    def validate_mind_map(self) -> Self:
        all_nodes = [el[0] for el in self.nodes]
        all_edges = [el[0] for el in self.edges] + [el[1] for el in self.edges]
        if set(all_nodes).issubset(set(all_edges)) and set(all_nodes) != set(all_edges):
            raise ValueError(
                "There are non-existing nodes listed as source or target in the edges"
            )
        return self
