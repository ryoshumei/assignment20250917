from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class WorkflowDB(Base):
    """
    Database model for workflows
    """
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    nodes = relationship("NodeDB", back_populates="workflow", order_by="NodeDB.order_index")
    runs = relationship("RunDB", back_populates="workflow", order_by="RunDB.started_at.desc()")
    jobs = relationship("JobDB", back_populates="workflow", order_by="JobDB.started_at.desc()")
    edges = relationship("EdgeDB", back_populates="workflow")


class NodeDB(Base):
    """
    Database model for workflow nodes
    """
    __tablename__ = "nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    node_type = Column(String, nullable=False)  # Store as TEXT per requirements
    config = Column(JSONB, nullable=False)  # Store configuration as JSONB
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("WorkflowDB", back_populates="nodes")
    run_nodes = relationship("RunNodeDB", back_populates="node")
    job_steps = relationship("JobStepDB", back_populates="node")
    outbound_edges = relationship("EdgeDB", foreign_keys="EdgeDB.from_node_id", back_populates="from_node")
    inbound_edges = relationship("EdgeDB", foreign_keys="EdgeDB.to_node_id", back_populates="to_node")

    # Index for performance
    __table_args__ = (
        Index("idx_nodes_workflow_order", "workflow_id", "order_index"),
    )


class RunDB(Base):
    """
    Database model for workflow runs
    """
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="Pending")  # Pending, Running, Succeeded, Failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    final_output = Column(Text, nullable=True)

    # Relationships
    workflow = relationship("WorkflowDB", back_populates="runs")
    run_nodes = relationship("RunNodeDB", back_populates="run", order_by="RunNodeDB.started_at")

    # Index for performance
    __table_args__ = (
        Index("idx_runs_workflow_started", "workflow_id", "started_at"),
    )


class RunNodeDB(Base):
    """
    Database model for individual node execution steps within a run
    """
    __tablename__ = "run_nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String, ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)  # Can be null if node deleted
    node_type = Column(String, nullable=False)  # Denormalized for auditability
    status = Column(String, nullable=False, default="Pending")  # Pending, Running, Succeeded, Failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    input_text = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    run = relationship("RunDB", back_populates="run_nodes")
    node = relationship("NodeDB", back_populates="run_nodes")

    # Index for performance
    __table_args__ = (
        Index("idx_run_nodes_run_started", "run_id", "started_at"),
    )


class JobDB(Base):
    """
    Database model for async workflow jobs
    """
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="Pending")  # Pending, Running, Succeeded, Failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    final_output = Column(Text, nullable=True)

    # Relationships
    workflow = relationship("WorkflowDB", back_populates="jobs")
    job_steps = relationship("JobStepDB", back_populates="job", order_by="JobStepDB.started_at")

    # Index for performance
    __table_args__ = (
        Index("idx_jobs_workflow_started", "workflow_id", "started_at"),
        Index("idx_jobs_status", "status"),
    )


class JobStepDB(Base):
    """
    Database model for individual node execution steps within a job
    """
    __tablename__ = "job_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String, ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True)  # Can be null if node deleted
    node_type = Column(String, nullable=False)  # Denormalized for auditability
    status = Column(String, nullable=False, default="Pending")  # Pending, Running, Succeeded, Failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    input_text = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    config_snapshot = Column(JSONB, nullable=True)  # Store node config at execution time

    # Relationships
    job = relationship("JobDB", back_populates="job_steps")
    node = relationship("NodeDB", back_populates="job_steps")

    # Index for performance
    __table_args__ = (
        Index("idx_job_steps_job_started", "job_id", "started_at"),
        Index("idx_job_steps_status", "status"),
    )


class UploadedFileDB(Base):
    """
    Database model for uploaded files (PDFs)
    """
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)  # Path where file is stored on disk
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Index for performance
    __table_args__ = (
        Index("idx_uploaded_files_created", "created_at"),
    )


class EdgeDB(Base):
    """
    Database model for workflow edges (DAG connections)
    """
    __tablename__ = "edges"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    from_node_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    from_port = Column(String, nullable=False, default="output")
    to_node_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    to_port = Column(String, nullable=False, default="input")
    condition = Column(String, nullable=True)  # Optional condition for conditional edges
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workflow = relationship("WorkflowDB", back_populates="edges")
    from_node = relationship("NodeDB", foreign_keys=[from_node_id], back_populates="outbound_edges")
    to_node = relationship("NodeDB", foreign_keys=[to_node_id], back_populates="inbound_edges")

    # Index for performance
    __table_args__ = (
        Index("idx_edges_workflow", "workflow_id"),
        Index("idx_edges_from_node", "from_node_id"),
        Index("idx_edges_to_node", "to_node_id"),
    )