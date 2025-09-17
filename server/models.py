from typing import List
from enum import Enum
from pydantic import BaseModel


class NodeType(str, Enum):
    EXTRACT_TEXT = "extract_text"
    GENERATIVE_AI = "generative_ai"
    FORMATTER = "formatter"


class Workflow(BaseModel):
    id: str
    name: str
    nodes: List["Node"]


class Node(BaseModel):
    id: str
    node_type: NodeType
    config: dict


# Resolve forward reference
Workflow.update_forward_refs()



