from dotenv import load_dotenv
import json
import os
import uuid
import warnings

from pydantic import BaseModel, Field, model_validator
from llama_index.core.llms import ChatMessage
from llama_cloud_services import LlamaExtract, LlamaParse
from llama_cloud_services.extract import SourceText
from llama_cloud.client import AsyncLlamaCloud
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.llms.openai import OpenAIResponses
from typing import List, Tuple, Union
from typing_extensions import Self
from pyvis.network import Network

load_dotenv()


class Node(BaseModel):
    id: str
    content: str


class Edge(BaseModel):
    from_id: str
    to_id: str


class MindMap(BaseModel):
    nodes: List[Node] = Field(
        description="List of nodes in the mind map, each represented as a Node object with an 'id' and concise 'content' (no more than 5 words).",
        examples=[
            [
                Node(id="A", content="Fall of the Roman Empire"),
                Node(id="B", content="476 AD"),
                Node(id="C", content="Barbarian invasions"),
            ],
            [
                Node(id="A", content="Auxin is released"),
                Node(id="B", content="Travels to the roots"),
                Node(id="C", content="Root cells grow"),
            ],
        ],
    )
    edges: List[Edge] = Field(
        description="The edges connecting the nodes of the mind map, as a list of Edge objects with from_id and to_id fields representing the source and target node IDs.",
        examples=[
            [
                Edge(from_id="A", to_id="B"),
                Edge(from_id="A", to_id="C"),
                Edge(from_id="B", to_id="C"),
            ],
            [
                Edge(from_id="C", to_id="A"),
                Edge(from_id="B", to_id="C"),
                Edge(from_id="A", to_id="B"),
            ],
        ],
    )

    @model_validator(mode="after")
    def validate_mind_map(self) -> Self:
        all_nodes = [el.id for el in self.nodes]
        all_edges = [el.from_id for el in self.edges] + [el.to_id for el in self.edges]
        if set(all_nodes).issubset(set(all_edges)) and set(all_nodes) != set(all_edges):
            raise ValueError(
                "There are non-existing nodes listed as source or target in the edges"
            )
        return self


class MindMapCreationFailedWarning(Warning):
    """A warning returned if the mind map creation failed"""


if (
    os.getenv("LLAMACLOUD_API_KEY", None)
    and os.getenv("EXTRACT_AGENT_ID", None)
    and os.getenv("LLAMACLOUD_PIPELINE_ID", None)
    and os.getenv("OPENAI_API_KEY", None)
):
    LLM = OpenAIResponses(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
    CLIENT = AsyncLlamaCloud(token=os.getenv("LLAMACLOUD_API_KEY"))
    EXTRACT_AGENT = LlamaExtract(api_key=os.getenv("LLAMACLOUD_API_KEY")).get_agent(
        id=os.getenv("EXTRACT_AGENT_ID")
    )
    PARSER = LlamaParse(api_key=os.getenv("LLAMACLOUD_API_KEY"), result_type="markdown")
    PIPELINE_ID = os.getenv("LLAMACLOUD_PIPELINE_ID")
    QE = LlamaCloudIndex(
        api_key=os.getenv("LLAMACLOUD_API_KEY"), pipeline_id=PIPELINE_ID
    ).as_query_engine(llm=LLM)
    LLM_STRUCT = LLM.as_structured_llm(MindMap)


async def process_file(
    filename: str,
) -> Union[Tuple[str, None], Tuple[None, None], Tuple[str, str]]:
    with open(filename, "rb") as f:
        file = await CLIENT.files.upload_file(upload_file=f)
    files = [{"file_id": file.id}]
    await CLIENT.pipelines.add_files_to_pipeline_api(
        pipeline_id=PIPELINE_ID, request=files
    )
    document = await PARSER.aparse(file_path=filename)
    md_content = await document.aget_markdown_documents()
    if len(md_content) == 0:
        return None, None
    text = "\n\n---\n\n".join([md.text for md in md_content])
    extraction_output = await EXTRACT_AGENT.aextract(
        files=SourceText(text_content=text, filename=file.name)
    )
    if extraction_output:
        return json.dumps(extraction_output.data, indent=4), text
    return None, None


async def get_mind_map(summary: str, highlights: List[str]) -> Union[str, None]:
    try:
        keypoints = "\n- ".join(highlights)
        messages = [
            ChatMessage(
                role="user",
                content=f"This is the summary for my document: {summary}\n\nAnd these are the key points:\n- {keypoints}",
            )
        ]
        response = await LLM_STRUCT.achat(messages=messages)
        response_json = json.loads(response.message.content)
        net = Network(directed=True, height="750px", width="100%")
        net.set_options("""
            var options = {
            "physics": {
                "enabled": false
            }
            }
            """)
        nodes = response_json["nodes"]
        edges = response_json["edges"]
        for node in nodes:
            net.add_node(n_id=node["id"], label=node["content"])
        for edge in edges:
            net.add_edge(source=edge["from_id"], to=edge["to_id"])
        name = str(uuid.uuid4())
        net.save_graph(name + ".html")
        return name + ".html"
    except Exception as e:
        warnings.warn(
            message=f"An error occurred during the creation of the mind map: {e}",
            category=MindMapCreationFailedWarning,
        )
        return None


async def query_index(question: str) -> Union[str, None]:
    response = await QE.aquery(question)
    if not response.response:
        return None
    sources = [node.text for node in response.source_nodes]
    return (
        "## Answer\n\n"
        + response.response
        + "\n\n## Sources\n\n- "
        + "\n- ".join(sources)
    )
