from pydantic import BaseModel
from typing import List
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



