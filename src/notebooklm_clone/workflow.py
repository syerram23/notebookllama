import json

from workflows import Workflow, step, Context
from workflows.events import StartEvent, StopEvent, Event
from workflows.resource import Resource
from llama_index.tools.mcp import BasicMCPClient
from typing import Annotated, List, Union

MCP_CLIENT = BasicMCPClient(command_or_url="http://localhost:8000/mcp")


class FileInputEvent(StartEvent):
    file: str


class ProcessedFileEvent(Event):
    pass


class NotebookOutputEvent(StopEvent):
    mind_map: str
    md_content: str


class MindMapCreationEvent(Event):
    summary: str
    highlights: List[str]
    md_content: str


def get_mcp_client(*args, **kwargs) -> BasicMCPClient:
    return MCP_CLIENT


class NotebookLMWorkflow(Workflow):
    @step
    async def extract_file_data(
        self,
        ev: FileInputEvent,
        mcp_client: Annotated[BasicMCPClient, Resource(get_mcp_client)],
        ctx: Context,
    ) -> Union[MindMapCreationEvent, NotebookOutputEvent]:
        ctx.write_event_to_stream(
            ev=ev,
        )
        result = await mcp_client.call_tool(
            tool_name="process_file_tool", arguments={"filename": ev.file}
        )
        ctx.write_event_to_stream(ev=ProcessedFileEvent())
        split_result = result.content[0].text.split("\n%separator%\n")
        json_data = split_result[0]
        md_text = split_result[1]
        if json_data == "Sorry, your file could not be processed.":
            return NotebookOutputEvent(
                mind_map="Unprocessable file, sorry😭", md_content=""
            )
        json_rep = json.loads(json_data)
        return MindMapCreationEvent(
            summary=json_rep["summary"],
            highlights=json_rep["highlights"],
            md_content=md_text,
        )

    @step
    async def generate_mind_map(
        self,
        ev: MindMapCreationEvent,
        mcp_client: Annotated[BasicMCPClient, Resource(get_mcp_client)],
        ctx: Context,
    ) -> NotebookOutputEvent:
        ctx.write_event_to_stream(
            ev=ev,
        )
        result = await mcp_client.call_tool(
            tool_name="process_file_tool",
            arguments={"summary": ev.summary, "highlights": ev.highlights},
        )
        if result is not None:
            return NotebookOutputEvent(
                mind_map=result.content[0].text, md_content=ev.md_content
            )
        return NotebookOutputEvent(
            mind_map="Sorry, mind map creation failed😭", md_content=ev.md_content
        )
