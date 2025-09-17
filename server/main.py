from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import logging
import uuid
import time

from .database import get_db
from .db_models import WorkflowDB, NodeDB, RunDB, RunNodeDB
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
)


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


@app.post("/workflows/{wf_id}/run")
def run_workflow(wf_id: str, request: Request, db: Session = Depends(get_db)):
    """Run a workflow (synchronous for this milestone)"""
    request_id = getattr(request.state, 'request_id', 'unknown')

    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == wf_id).first()
    if not workflow:
        logger.warning(
            "Workflow not found",
            extra={"request_id": request_id, "workflow_id": wf_id}
        )
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create run record
    run = RunDB(workflow_id=wf_id, status="Running")
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info(
        "Workflow execution started",
        extra={
            "request_id": request_id,
            "workflow_id": wf_id,
            "run_id": run.id,
            "node_count": len(workflow.nodes)
        }
    )

    try:
        # Execute workflow nodes in order
        data = {"text": "Initial text from some doc ..."}

        for i, node in enumerate(workflow.nodes):
            # Create run_node record for this step
            run_node = RunNodeDB(
                run_id=run.id,
                node_id=node.id,
                node_type=node.node_type,
                status="Running",
                input_text=data["text"]
            )
            db.add(run_node)
            db.commit()
            db.refresh(run_node)

            logger.info(
                "Node execution started",
                extra={
                    "request_id": request_id,
                    "workflow_id": wf_id,
                    "run_id": run.id,
                    "run_node_id": run_node.id,
                    "node_id": node.id,
                    "node_type": node.node_type,
                    "node_index": i
                }
            )

            try:
                # Simulate node execution
                if node.node_type == NodeType.EXTRACT_TEXT.value:
                    data["text"] = "[EXTRACTED] " + data["text"]
                elif node.node_type == NodeType.GENERATIVE_AI.value:
                    prompt = node.config.get("prompt", "")
                    data["text"] = f"[GEN_AI with prompt='{prompt}']: " + data["text"]
                elif node.node_type == NodeType.FORMATTER.value:
                    data["text"] = data["text"].upper()

                # Update run_node as succeeded
                run_node.status = "Succeeded"
                run_node.finished_at = datetime.utcnow()
                run_node.output_text = data["text"]
                db.commit()

                logger.info(
                    "Node execution completed",
                    extra={
                        "request_id": request_id,
                        "workflow_id": wf_id,
                        "run_id": run.id,
                        "run_node_id": run_node.id,
                        "node_id": node.id,
                        "node_type": node.node_type,
                        "status": "Succeeded"
                    }
                )

            except Exception as e:
                # Handle node execution failure
                run_node.status = "Failed"
                run_node.finished_at = datetime.utcnow()
                run_node.error_message = str(e)
                db.commit()

                logger.error(
                    "Node execution failed",
                    extra={
                        "request_id": request_id,
                        "workflow_id": wf_id,
                        "run_id": run.id,
                        "run_node_id": run_node.id,
                        "node_id": node.id,
                        "node_type": node.node_type,
                        "error": str(e)
                    }
                )
                raise

        # Mark run as succeeded
        run.status = "Succeeded"
        run.finished_at = datetime.utcnow()
        run.final_output = data["text"]
        db.commit()

        logger.info(
            "Workflow execution completed successfully",
            extra={
                "request_id": request_id,
                "workflow_id": wf_id,
                "run_id": run.id,
                "status": "Succeeded",
                "nodes_executed": len(workflow.nodes)
            }
        )

        return {"final_output": data["text"]}

    except Exception as e:
        # Mark run as failed
        run.status = "Failed"
        run.finished_at = datetime.utcnow()
        run.error_message = str(e)
        db.commit()

        logger.error(
            "Workflow execution failed",
            extra={
                "request_id": request_id,
                "workflow_id": wf_id,
                "run_id": run.id,
                "status": "Failed",
                "error": str(e)
            }
        )

        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@app.get("/workflows/{wf_id}/runs", response_model=WorkflowRunsResponse)
def get_workflow_runs(wf_id: str, db: Session = Depends(get_db)):
    """List runs for a workflow"""
    workflow = db.query(WorkflowDB).filter(WorkflowDB.id == wf_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    runs = db.query(RunDB).filter(RunDB.workflow_id == wf_id).order_by(RunDB.started_at.desc()).all()

    return WorkflowRunsResponse(
        runs=[RunResponse.from_orm(run) for run in runs]
    )


@app.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run_detail(run_id: str, db: Session = Depends(get_db)):
    """Get run detail with steps"""
    run = db.query(RunDB).filter(RunDB.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run_nodes = db.query(RunNodeDB).filter(RunNodeDB.run_id == run_id).order_by(RunNodeDB.started_at).all()

    return RunDetailResponse(
        run=RunResponse.from_orm(run),
        steps=[RunNodeResponse.from_orm(rn) for rn in run_nodes]
    )