import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import uuid

from ..db_models import JobDB, JobStepDB, WorkflowDB, NodeDB, UploadedFileDB
from ..models import NodeType
from .pdf_service import pdf_service
from .llm_service import llm_service
from .formatter_service import formatter_service

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
                # Execute workflow nodes in order
                current_text = "Initial text from document"  # Default starting text

                for i, node in enumerate(workflow.nodes):
                    # Create job step record
                    job_step = JobStepDB(
                        job_id=job.id,
                        node_id=node.id,
                        node_type=node.node_type,
                        status="Running",
                        input_text=current_text,
                        config_snapshot=node.config
                    )
                    db.add(job_step)
                    db.commit()
                    db.refresh(job_step)

                    logger.info(f"Executing node {node.id} ({node.node_type}) for job {job_id}")

                    try:
                        # Execute node based on type
                        if node.node_type == NodeType.EXTRACT_TEXT.value:
                            current_text = await self._execute_extract_text_node(node.config, current_text, db)
                        elif node.node_type == NodeType.GENERATIVE_AI.value:
                            current_text = await self._execute_generative_ai_node(node.config, current_text)
                        elif node.node_type == NodeType.FORMATTER.value:
                            current_text = await self._execute_formatter_node(node.config, current_text)
                        else:
                            raise ValueError(f"Unknown node type: {node.node_type}")

                        # Update job step as succeeded
                        job_step.status = "Succeeded"
                        job_step.finished_at = datetime.utcnow()
                        job_step.output_text = current_text
                        db.commit()

                        logger.info(f"Node {node.id} completed successfully for job {job_id}")

                    except Exception as e:
                        # Handle node execution failure
                        job_step.status = "Failed"
                        job_step.finished_at = datetime.utcnow()
                        job_step.error_message = str(e)
                        db.commit()

                        logger.error(f"Node {node.id} failed for job {job_id}: {str(e)}")
                        raise

                # Mark job as succeeded
                job.status = "Succeeded"
                job.finished_at = datetime.utcnow()
                job.final_output = current_text
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


# Global service instance
job_service = JobService()