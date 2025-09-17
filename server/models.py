from typing import List
from enum import Enum
from pydantic import BaseModel


class NodeType(str, Enum):
    EXTRACT_TEXT = "extract_text"
    GENERATIVE_AI = "generative_ai"
    FORMATTER = "formatter"
    AGENT = "agent"


class Workflow(BaseModel):
    id: str
    name: str
    nodes: List["Node"]


class Node(BaseModel):
    id: str
    node_type: NodeType
    config: dict


class Edge(BaseModel):
    id: str
    workflow_id: str
    from_node_id: str
    from_port: str = "output"
    to_node_id: str
    to_port: str = "input"
    condition: str = None


# Resolve forward reference
Workflow.update_forward_refs()



