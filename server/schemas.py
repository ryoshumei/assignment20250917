from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .models import NodeType


class CreateWorkflowRequest(BaseModel):
    name: str


class CreateWorkflowResponse(BaseModel):
    id: str
    name: str


class AddNodeRequest(BaseModel):
    node_type: NodeType
    config: dict


class WorkflowDetailResponse(BaseModel):
    id: str
    name: str
    nodes: List[dict]


# New schemas for run history
class RunResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    final_output: Optional[str] = None

    class Config:
        orm_mode = True


class RunNodeResponse(BaseModel):
    id: str
    run_id: str
    node_id: Optional[str] = None
    node_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_text: Optional[str] = None
    output_text: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        orm_mode = True


class WorkflowRunsResponse(BaseModel):
    runs: List[RunResponse]


class RunDetailResponse(BaseModel):
    run: RunResponse
    steps: List[RunNodeResponse]



