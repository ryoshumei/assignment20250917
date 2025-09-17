from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import logging
import uuid
import time
import os

from .database import get_db
from .db_models import WorkflowDB, NodeDB, RunDB, RunNodeDB, JobDB, JobStepDB, UploadedFileDB
from .models import NodeType
from .schemas import (
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    AddNodeRequest,
    WorkflowDetailResponse,
    WorkflowRunsResponse,
    RunDetailResponse,
    RunResponse,
    RunNodeResponse,
    JobAccepted,
    Job,
    JobDetailResponse,
    JobStepResponse,
    FileUploadResponse,
)
from .services.pdf_service import pdf_service
from .services.llm_service import llm_service
from .services.formatter_service import formatter_service
from .services.job_service import job_service


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Workflow App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_logging(request: Request, call_next):
    """Add request ID to all requests and log request/response info"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.time()

    # Log request
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None
        }
    )

    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": round(process_time, 4)
        }
    )

    response.headers["X-Request-ID"] = request_id
    return response


@app.post("/workflows", response_model=CreateWorkflowResponse)
def create_workflow(req: CreateWorkflowRequest, db: Session = Depends(get_db)):
    """Create a new workflow"""
    workflow = WorkflowDB(name=req.name)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return CreateWorkflowResponse(id=workflow.id, name=workflow.name)


@app.get("/workflows/{wf_id}", response_model=WorkflowDetailResponse)
def get_workflow(wf_id: str, db: Session = Depends(get_db)):
    """Get workflow by ID with nodes in order"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == wf_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Convert nodes to dict format for response
    nodes = []
    for node in workflow.nodes:  # Already ordered by order_index due to relationship
        nodes.append({
            "id": node.id,
            "node_type": node.node_type,
            "config": node.config
        })

    return WorkflowDetailResponse(
        id=workflow.id,
        name=workflow.name,
        nodes=nodes
    )


@app.post("/workflows/{wf_id}/nodes")
def add_node(wf_id: str, req: AddNodeRequest, db: Session = Depends(get_db)):
    """Add a node to a workflow"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == wf_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Validate node configuration based on type
    if req.node_type == NodeType.GENERATIVE_AI:
        is_valid, error_msg = llm_service.validate_config(req.config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
    elif req.node_type == NodeType.FORMATTER:
        is_valid, error_msg = formatter_service.validate_config(req.config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

    # Get the next order index
    max_order = db.query(NodeDB).filter(NodeDB.workflow_id == wf_id).count()

    node = NodeDB(
        workflow_id=wf_id,
        node_type=req.node_type.value,
        config=req.config,
        order_index=max_order
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    return {"message": "Node added", "node_id": node.id}


@app.post("/workflows/{wf_id}/run", response_model=JobAccepted)
def run_workflow(wf_id: str, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    """Run a workflow asynchronously"""
    request_id = getattr(request.state, 'request_id', 'unknown')

    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == wf_id).first()
    if not workflow:
        logger.warning(
            "Workflow not found",
            extra={"request_id": request_id, "workflow_id": wf_id}
        )
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create job record
    try:
        job = job_service.create_job(db, wf_id)

        # Try to enqueue the job
        if not job_service.enqueue_job(wf_id, job.id):
            # Queue is full
            db.delete(job)
            db.commit()
            raise HTTPException(
                status_code=429,
                detail="Job queue is full. Maximum concurrent jobs reached. Please try again later."
            )

        # Add job execution to background tasks
        background_tasks.add_task(job_service.execute_job, db, job.id)

        logger.info(
            "Workflow job enqueued",
            extra={
                "request_id": request_id,
                "workflow_id": wf_id,
                "job_id": job.id
            }
        )

        return JobAccepted(job_id=job.id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating job",
            extra={
                "request_id": request_id,
                "workflow_id": wf_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create job")


@app.get("/workflows/{wf_id}/runs", response_model=WorkflowRunsResponse)
def get_workflow_runs(wf_id: str, db: Session = Depends(get_db)):
    """List runs for a workflow (includes both traditional runs and async jobs)"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == wf_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Get traditional runs
    runs = db.query(RunDB).filter(RunDB.workflow_id == wf_id).order_by(RunDB.started_at.desc()).all()

    # Get async jobs (convert to run format for backward compatibility)
    jobs = db.query(JobDB).filter(JobDB.workflow_id == wf_id).order_by(JobDB.started_at.desc()).all()

    # Convert jobs to run format
    run_responses = [RunResponse.from_orm(run) for run in runs]

    for job in jobs:
        # Create a run-like response for jobs
        job_as_run = RunResponse(
            id=job.id,
            workflow_id=job.workflow_id,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_message=job.error_message,
            final_output=job.final_output
        )
        run_responses.append(job_as_run)

    # Sort all runs by started_at descending
    run_responses.sort(key=lambda x: x.started_at, reverse=True)

    return WorkflowRunsResponse(runs=run_responses)


@app.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Get run detail with steps (supports both traditional runs and async jobs)"""
    # First try to find a traditional run
    run = db.query(RunDB).filter(RunDB.id == run_id).first()
    if run:
        run_nodes = db.query(RunNodeDB).filter(RunNodeDB.run_id == run_id).order_by(RunNodeDB.started_at).all()
        return RunDetailResponse(
            run=RunResponse.from_orm(run),
            steps=[RunNodeResponse.from_orm(rn) for rn in run_nodes]
        )

    # If not found, try to find an async job
    job = db.query(JobDB).filter(JobDB.id == run_id).first()
    if job:
        job_steps = db.query(JobStepDB).filter(JobStepDB.job_id == run_id).order_by(JobStepDB.started_at).all()

        # Convert job to run format for backward compatibility
        job_as_run = RunResponse(
            id=job.id,
            workflow_id=job.workflow_id,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error_message=job.error_message,
            final_output=job.final_output
        )

        # Convert job steps to run node format
        steps_as_run_nodes = []
        for step in job_steps:
            step_as_run_node = RunNodeResponse(
                id=step.id,
                run_id=step.job_id,
                node_id=step.node_id,
                node_type=step.node_type,
                status=step.status,
                started_at=step.started_at,
                finished_at=step.finished_at,
                input_text=step.input_text,
                output_text=step.output_text,
                error_message=step.error_message
            )
            steps_as_run_nodes.append(step_as_run_node)

        return RunDetailResponse(
            run=job_as_run,
            steps=steps_as_run_nodes
        )

    raise HTTPException(status_code=404, detail="Run not found")


@app.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job status and details"""
    job = db.query(JobDB).filter(JobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return Job.from_orm(job)


@app.get("/jobs/{job_id}/details", response_model=JobDetailResponse)
def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """Get job details with steps"""
    job = db.query(JobDB).filter(JobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_steps = db.query(JobStepDB).filter(JobStepDB.job_id == job_id).order_by(JobStepDB.started_at).all()

    return JobDetailResponse(
        job=Job.from_orm(job),
        steps=[JobStepResponse.from_orm(step) for step in job_steps]
    )


@app.post("/files", response_model=FileUploadResponse)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF file"""
    try:
        # Validate PDF file
        is_valid, error_msg = pdf_service.validate_pdf(file)
        if not is_valid:
            # Check if it's a file size error for proper HTTP status code
            if error_msg and error_msg.startswith("FILE_TOO_LARGE:"):
                raise HTTPException(status_code=413, detail=error_msg.replace("FILE_TOO_LARGE:", ""))
            else:
                raise HTTPException(status_code=400, detail=error_msg)

        # Store file
        file_id, file_path = pdf_service.store_file(file)

        # Save file record to database
        uploaded_file = UploadedFileDB(
            id=file_id,
            filename=file.filename or "uploaded.pdf",
            mime_type=file.content_type or "application/pdf",
            size_bytes=len(file.file.read()),
            file_path=file_path
        )

        # Reset file pointer and get actual size
        file.file.seek(0)
        content = file.file.read()
        uploaded_file.size_bytes = len(content)

        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)

        logger.info(f"File uploaded successfully: {file_id}")

        return FileUploadResponse(
            file_id=file_id,
            filename=uploaded_file.filename,
            size=uploaded_file.size_bytes
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")