from dotenv import load_dotenv
import json
import os
import uuid

from models import MindMap
from llama_index.core.llms import ChatMessage
from llama_index.core.query_engine.multistep_query_engine import MultiStepQueryEngine
from llama_index.core.indices.query.query_transform import StepDecomposeQueryTransform
from llama_cloud_services import LlamaExtract
from llama_cloud.client import AsyncLlamaCloud
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.llms.openai import OpenAIResponses
from typing import Union, List
from pyvis.network import Network


load_dotenv()

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
    PIPELINE_ID = os.getenv("LLAMACLOUD_PIPELINE_ID")
    qe = LlamaCloudIndex(
        api_key=os.getenv("LLAMACLOUD_API_KEY"), pipeline_id=PIPELINE_ID
    ).as_query_engine(llm=LLM)
    step_decompose = StepDecomposeQueryTransform(llm=LLM)
    MS_QE = MultiStepQueryEngine(query_engine=qe, query_transform=step_decompose)
    LLM_STRUCT = LLM.as_structured_llm(MindMap)


async def process_file(filename: str) -> Union[str, None]:
    with open(filename, "rb") as f:
        file = await CLIENT.files.upload_file(upload_file=f)
    files = [{"file_id": file.id}]
    await CLIENT.pipelines.add_files_to_pipeline_api(
        pipeline_id=PIPELINE_ID, request=files
    )
    extraction_output = await EXTRACT_AGENT.aextract(files=filename)
    if extraction_output:
        return json.dumps(extraction_output.data, indent=4)
    return None


async def get_mind_map(summary: str, highlights: List[str]):
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
