from dotenv import load_dotenv
import json
import os
import uuid
import warnings

from pydantic import BaseModel, Field, model_validator
from llama_index.core.llms import ChatMessage
from llama_index.core.query_engine.multistep_query_engine import MultiStepQueryEngine
from llama_index.core.indices.query.query_transform import StepDecomposeQueryTransform
from llama_cloud_services import LlamaExtract, LlamaParse
from llama_cloud.client import AsyncLlamaCloud
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.llms.openai import OpenAIResponses
from typing import List, Tuple, Union
from typing_extensions import Self
from pyvis.network import Network

load_dotenv()


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
    qe = LlamaCloudIndex(
        api_key=os.getenv("LLAMACLOUD_API_KEY"), pipeline_id=PIPELINE_ID
    ).as_query_engine(llm=LLM)
    step_decompose = StepDecomposeQueryTransform(llm=LLM)
    MS_QE = MultiStepQueryEngine(query_engine=qe, query_transform=step_decompose)
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
    extraction_output = await EXTRACT_AGENT.aextract(files=filename)
    document = await PARSER.aparse(file_path=filename)
    md_content = await document.aget_markdown_documents()
    if extraction_output:
        if len(md_content) > 0:
            text = "\n\n---\n\n".join([md.text for md in md_content])
            return json.dumps(extraction_output.data, indent=4), text
        return json.dumps(extraction_output.data, indent=4), None
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
        nodes = response_json["nodes"]
        edges = response_json["edges"]
        for node in nodes:
            net.add_node(n_id=node[0], label=node[1])
        for edge in edges:
            net.add_edge(source=edge[0], to=edge[1])
        name = str(uuid.uuid4())
        net.save_graph(name)
        return name + ".html"
    except Exception as e:
        warnings.warn(
            message=f"An error occurred during the creation of the mind map: {e}",
            category=MindMapCreationFailedWarning,
        )
        return None
