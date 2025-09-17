import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import uuid

from ..db_models import JobDB, JobStepDB, WorkflowDB, NodeDB, UploadedFileDB, EdgeDB
from ..models import NodeType
from .pdf_service import pdf_service
from .llm_service import llm_service
from .formatter_service import formatter_service
from .graph_service import topo_schedule, get_node_dependencies, aggregate_inputs
from .agent_service import execute_agent_bounded

logger = logging.getLogger(__name__)

class JobQueue:
    """Manages job queue with concurrency limits"""

    def __init__(self, max_concurrent_per_workflow: int = 2, max_queue_size: int = 20):
        self.max_concurrent_per_workflow = max_concurrent_per_workflow
        self.max_queue_size = max_queue_size
        self.running_jobs: Dict[str, List[str]] = {}  # workflow_id -> [job_ids]
        self.pending_queue: List[str] = []  # job_ids in FIFO order

    def can_enqueue(self, workflow_id: str) -> bool:
        """Check if a new job can be enqueued"""
        # Check global queue capacity
        if len(self.pending_queue) >= self.max_queue_size:
            return False

        # Check workflow-specific running job limit
        running_count = len(self.running_jobs.get(workflow_id, []))
        return running_count < self.max_concurrent_per_workflow

    def enqueue_job(self, workflow_id: str, job_id: str) -> bool:
        """Enqueue a job if possible"""
        if not self.can_enqueue(workflow_id):
            return False

        # If we can run immediately, add to running jobs
        running_count = len(self.running_jobs.get(workflow_id, []))
        if running_count < self.max_concurrent_per_workflow:
            if workflow_id not in self.running_jobs:
                self.running_jobs[workflow_id] = []
            self.running_jobs[workflow_id].append(job_id)
            logger.info(f"Job {job_id} added to running jobs for workflow {workflow_id}")
            return True

        # Otherwise add to pending queue
        self.pending_queue.append(job_id)
        logger.info(f"Job {job_id} added to pending queue")
        return True

    def job_completed(self, workflow_id: str, job_id: str) -> Optional[str]:
        """
        Mark job as completed and return next job to start if any
        Returns: job_id of next job to start, or None
        """
        # Remove from running jobs
        if workflow_id in self.running_jobs:
            if job_id in self.running_jobs[workflow_id]:
                self.running_jobs[workflow_id].remove(job_id)
                logger.info(f"Job {job_id} removed from running jobs for workflow {workflow_id}")

        # Check if we can start a pending job for this workflow
        running_count = len(self.running_jobs.get(workflow_id, []))
        if running_count < self.max_concurrent_per_workflow and self.pending_queue:
            next_job_id = self.pending_queue.pop(0)
            if workflow_id not in self.running_jobs:
                self.running_jobs[workflow_id] = []
            self.running_jobs[workflow_id].append(next_job_id)
            logger.info(f"Started pending job {next_job_id} for workflow {workflow_id}")
            return next_job_id

        return None


class JobService:
    """Service for managing async job execution"""

    def __init__(self):
        self.job_queue = JobQueue()

    def create_job(self, db: Session, workflow_id: str) -> JobDB:
        """Create a new job record"""
        try:
            # Check if workflow exists
            workflow = db.query(WorkflowDB).filter(WorkflowDB.id == workflow_id).first()
            if not workflow:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Create job record
            job = JobDB(
                workflow_id=workflow_id,
                status="Pending"
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            logger.info(f"Created job {job.id} for workflow {workflow_id}")
            return job

        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            db.rollback()
            raise

    def enqueue_job(self, workflow_id: str, job_id: str) -> bool:
        """Enqueue job for execution"""
        return self.job_queue.enqueue_job(workflow_id, job_id)

    async def execute_job(self, db: Session, job_id: str):
        """Execute a job asynchronously"""
        try:
            # Get job and workflow
            job = db.query(JobDB).filter(JobDB.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            workflow = db.query(WorkflowDB).filter(WorkflowDB.id == job.workflow_id).first()
            if not workflow:
                logger.error(f"Workflow {job.workflow_id} not found")
                return

            # Update job status to Running
            job.status = "Running"
            db.commit()

            logger.info(f"Starting execution of job {job_id} for workflow {job.workflow_id}")

            try:
                # Get workflow edges for DAG execution
                edges = db.query(EdgeDB).filter(EdgeDB.workflow_id == job.workflow_id).all()
                nodes = workflow.nodes

                # If no edges, fall back to linear execution
                if not edges:
                    await self._execute_linear_workflow(job, nodes, db)
                else:
                    await self._execute_dag_workflow(job, nodes, edges, db)

                # Mark job as succeeded
                job.status = "Succeeded"
                job.finished_at = datetime.utcnow()
                # Get final output from the last executed nodes
                final_outputs = []
                for step in db.query(JobStepDB).filter(JobStepDB.job_id == job.id, JobStepDB.status == "Succeeded").all():
                    if step.output_text:
                        final_outputs.append(step.output_text)

                job.final_output = "\n\n".join(final_outputs[-3:]) if final_outputs else "No output generated"
                db.commit()

                logger.info(f"Job {job_id} completed successfully")

            except Exception as e:
                # Mark job as failed
                job.status = "Failed"
                job.finished_at = datetime.utcnow()
                job.error_message = str(e)
                db.commit()

                logger.error(f"Job {job_id} failed: {str(e)}")

        except Exception as e:
            logger.error(f"Error executing job {job_id}: {str(e)}")

        finally:
            # Notify queue that job is completed
            try:
                next_job_id = self.job_queue.job_completed(job.workflow_id, job_id)
                if next_job_id:
                    # Start next job in queue
                    asyncio.create_task(self.execute_job(db, next_job_id))
            except Exception as e:
                logger.error(f"Error handling job completion: {str(e)}")

    async def _execute_linear_workflow(self, job: JobDB, nodes: List[NodeDB], db: Session):
        """Execute workflow nodes in linear order (fallback when no edges)"""
        current_text = "Initial text from document"  # Default starting text

        for i, node in enumerate(nodes):
            current_text = await self._execute_single_node(job, node, current_text, db)

    async def _execute_dag_workflow(self, job: JobDB, nodes: List[NodeDB], edges: List[EdgeDB], db: Session):
        """Execute workflow using DAG topological scheduling with AND-join semantics"""
        # Create node lookup
        node_map = {node.id: node for node in nodes}
        node_outputs = {}  # node_id -> output_text

        # Use topological scheduling to get execution batches
        for batch in topo_schedule(edges, nodes):
            # Execute all nodes in this batch in parallel
            batch_tasks = []
            for node_id in batch:
                node = node_map[node_id]

                # Get dependencies and aggregate inputs
                dependencies = get_node_dependencies(node_id, edges)
                input_text = aggregate_inputs(dependencies, node_outputs)

                # If no dependencies, use default starting text
                if not input_text and not dependencies:
                    input_text = "Initial text from document"

                # Create task for parallel execution
                task = self._execute_single_node(job, node, input_text, db)
                batch_tasks.append((node_id, task))

            # Execute batch in parallel and collect outputs
            for node_id, task in batch_tasks:
                try:
                    output = await task
                    node_outputs[node_id] = output
                    logger.info(f"Node {node_id} in batch completed successfully")
                except Exception as e:
                    logger.error(f"Node {node_id} in batch failed: {str(e)}")
                    raise

    async def _execute_single_node(self, job: JobDB, node: NodeDB, input_text: str, db: Session) -> str:
        """Execute a single node and return its output"""
        # Create job step record
        job_step = JobStepDB(
            job_id=job.id,
            node_id=node.id,
            node_type=node.node_type,
            status="Running",
            input_text=input_text,
            config_snapshot=node.config
        )
        db.add(job_step)
        db.commit()
        db.refresh(job_step)

        logger.info(f"Executing node {node.id} ({node.node_type}) for job {job.id}")

        try:
            # Execute node based on type
            if node.node_type == NodeType.EXTRACT_TEXT.value:
                output = await self._execute_extract_text_node(node.config, input_text, db)
            elif node.node_type == NodeType.GENERATIVE_AI.value:
                output = await self._execute_generative_ai_node(node.config, input_text)
            elif node.node_type == NodeType.FORMATTER.value:
                output = await self._execute_formatter_node(node.config, input_text)
            elif node.node_type == NodeType.AGENT.value:
                output = await self._execute_agent_node(node.config, input_text)
            else:
                raise ValueError(f"Unknown node type: {node.node_type}")

            # Update job step as succeeded
            job_step.status = "Succeeded"
            job_step.finished_at = datetime.utcnow()
            job_step.output_text = output
            db.commit()

            logger.info(f"Node {node.id} completed successfully for job {job.id}")
            return output

        except Exception as e:
            # Handle node execution failure
            job_step.status = "Failed"
            job_step.finished_at = datetime.utcnow()
            job_step.error_message = str(e)
            db.commit()

            logger.error(f"Node {node.id} failed for job {job.id}: {str(e)}")
            raise

    async def _execute_extract_text_node(self, config: Dict, input_text: str, db: Session = None) -> str:
        """Execute extract_text node"""
        try:
            if "file_id" in config:
                # Extract text from uploaded file
                file_id = config["file_id"]

                # Get file record from database
                if db:
                    uploaded_file = db.query(UploadedFileDB).filter(UploadedFileDB.id == file_id).first()
                    if not uploaded_file:
                        raise ValueError(f"File {file_id} not found in database")

                    # Extract text from the file
                    extracted_text = pdf_service.extract_text(uploaded_file.file_path)
                    return extracted_text
                else:
                    # Fallback when no db session available
                    return f"[EXTRACTED from file {file_id}] Could not access file - no database session"
            else:
                # Use input text as fallback
                return f"[EXTRACTED] {input_text}"

        except Exception as e:
            logger.error(f"Error in extract_text node: {str(e)}")
            raise

    async def _execute_generative_ai_node(self, config: Dict, input_text: str) -> str:
        """Execute generative_ai node"""
        try:
            return await llm_service.call_llm(input_text, config)
        except Exception as e:
            logger.error(f"Error in generative_ai node: {str(e)}")
            raise

    async def _execute_formatter_node(self, config: Dict, input_text: str) -> str:
        """Execute formatter node"""
        try:
            return formatter_service.format_text(input_text, config)
        except Exception as e:
            logger.error(f"Error in formatter node: {str(e)}")
            raise

    async def _execute_agent_node(self, config: Dict, input_text: str) -> str:
        """Execute agent node with bounded execution"""
        try:
            # Structured logging for agent execution start
            logger.info(
                "Agent node execution started",
                extra={
                    "node_type": "agent",
                    "objective": config.get('objective', 'unknown'),
                    "tools": config.get('tools', []),
                    "max_iterations": config.get('max_iterations', 5),
                    "timeout_seconds": config.get('timeout_seconds', 30),
                    "input_length": len(input_text)
                }
            )

            result = await execute_agent_bounded(config, input_text)

            # Redact PII from output for logging
            output_text = result.get('output_text', input_text)
            redacted_output = self._redact_sensitive_data(output_text)

            # Structured logging for agent execution completion
            logger.info(
                "Agent node execution completed",
                extra={
                    "node_type": "agent",
                    "termination_reason": result.get('termination_reason', 'unknown'),
                    "iterations": result.get('iterations', 0),
                    "execution_time": result.get('execution_time', 0),
                    "output_length": len(output_text),
                    "redacted_output_preview": redacted_output[:100] if redacted_output else None
                }
            )

            return output_text

        except Exception as e:
            # Structured error logging
            logger.error(
                "Agent node execution failed",
                extra={
                    "node_type": "agent",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "objective": config.get('objective', 'unknown')
                }
            )
            raise

    def _redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive information from text for logging"""
        import re

        if not text:
            return text

        # Redact common PII patterns
        redacted = text

        # Email addresses
        redacted = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', redacted)

        # Phone numbers (basic patterns)
        redacted = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE_REDACTED]', redacted)
        redacted = re.sub(r'\b\(\d{3}\)\s*\d{3}-\d{4}\b', '[PHONE_REDACTED]', redacted)

        # Credit card numbers (basic 16-digit pattern)
        redacted = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]', redacted)

        # Social Security Numbers
        redacted = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', redacted)

        # API keys and tokens (common patterns)
        redacted = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[TOKEN_REDACTED]', redacted)

        return redacted


# Global service instance
job_service = JobService()