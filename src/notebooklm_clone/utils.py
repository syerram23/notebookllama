from dotenv import load_dotenv
import os

from llama_cloud_services import LlamaExtract
from llama_cloud.client import AsyncLlamaCloud
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.llms.openai import OpenAI


load_dotenv()


load_dotenv()
if (
    os.getenv("LLAMACLOUD_API_KEY", None)
    and os.getenv("EXTRACT_AGENT_ID", None)
    and os.getenv("LLAMACLOUD_PIPELINE_ID", None)
    and os.getenv("OPENAI_API_KEY", None)
):
    LLM = OpenAI(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
    CLIENT = AsyncLlamaCloud(token=os.getenv("LLAMACLOUD_API_KEY"))
    EXTRACT_AGENT = LlamaExtract(api_key=os.getenv("LLAMACLOUD_API_KEY")).get_agent(
        id=os.getenv("EXTRACT_AGENT_ID")
    )
    PIPELINE_ID = os.getenv("LLAMACLOUD_PIPELINE_ID")
    QE = LlamaCloudIndex(
        api_key=os.getenv("LLAMACLOUD_API_KEY"), pipeline_id=PIPELINE_ID
    ).as_query_engine(llm=LLM)
