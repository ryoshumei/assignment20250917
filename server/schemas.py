from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
from .models import NodeType


class JobStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"


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


# New schemas for async job operations
class JobAccepted(BaseModel):
    job_id: str


class Job(BaseModel):
    id: str
    workflow_id: str
    status: JobStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    final_output: Optional[str] = None

    class Config:
        orm_mode = True


class JobStepResponse(BaseModel):
    id: str
    job_id: str
    node_id: Optional[str] = None
    node_type: str
    status: JobStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    input_text: Optional[str] = None
    output_text: Optional[str] = None
    error_message: Optional[str] = None
    config_snapshot: Optional[dict] = None

    class Config:
        orm_mode = True


class JobDetailResponse(BaseModel):
    job: Job
    steps: List[JobStepResponse]


# File upload schemas
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int



