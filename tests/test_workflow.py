from src.notebooklm_clone.workflow import NotebookLMWorkflow
from workflows import Workflow


def test_init() -> None:
    wf = NotebookLMWorkflow(disable_validation=True)
    assert isinstance(wf, Workflow)
    assert list(wf._get_steps().keys()) == [
        "_done",
        "extract_file_data",
        "generate_mind_map",
    ]
