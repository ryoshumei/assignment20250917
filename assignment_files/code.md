**Application Structure**

```
.
├── server
│   ├── main.py            # Entry point for FastAPI
│   ├── models.py          # Pydantic models, enums, etc.
│   ├── schemas.py         # Request/response schemas
│   └── requirements.txt   # Python dependencies
└── client
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts     # Vite config for running React
    └── src
        ├── App.tsx        # Root React component
        ├── api.ts         # API wrapper for backend communication
        └── types.ts       # TypeScript type definitions
```

server/requirements.txt

```
fastapi==0.95.0
uvicorn==0.22.0
pydantic==1.10.5
```

server/models.py

```py
from typing import List, Optional
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
    config: dict  # Node-specific parameters (e.g., prompt, model name)

# Resolve forward reference
Workflow.update_forward_refs()
```

server/schemas.py

```py
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
```

server/main.py

```py
from fastapi import FastAPI, HTTPException
from uuid import uuid4

from .models import Workflow, Node, NodeType
from .schemas import (
    CreateWorkflowRequest, CreateWorkflowResponse,
    AddNodeRequest, WorkflowDetailResponse
)

app = FastAPI(title="Workflow App")

# In-memory storage for simplicity
workflows = {}

@app.post("/workflows", response_model=CreateWorkflowResponse)
def create_workflow(req: CreateWorkflowRequest):
    wf_id = str(uuid4())
    new_wf = Workflow(id=wf_id, name=req.name, nodes=[])
    workflows[wf_id] = new_wf
    return CreateWorkflowResponse(id=wf_id, name=req.name)

@app.get("/workflows/{wf_id}", response_model=WorkflowDetailResponse)
def get_workflow(wf_id: str):
    wf = workflows.get(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowDetailResponse(
        id=wf.id,
        name=wf.name,
        nodes=[node.dict() for node in wf.nodes]
    )

@app.post("/workflows/{wf_id}/nodes")
def add_node(wf_id: str, req: AddNodeRequest):
    wf = workflows.get(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    node_id = str(uuid4())
    new_node = Node(id=node_id, node_type=req.node_type, config=req.config)
    wf.nodes.append(new_node)
    return {"message": "Node added", "node_id": node_id}

@app.post("/workflows/{wf_id}/run")
def run_workflow(wf_id: str):
    wf = workflows.get(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Simple simulation of node execution
    data = {"text": "Initial text from some doc ..."}
    for node in wf.nodes:
        if node.node_type == NodeType.EXTRACT_TEXT:
            data["text"] = "[EXTRACTED] " + data["text"]
        elif node.node_type == NodeType.GENERATIVE_AI:
            prompt = node.config.get("prompt", "")
            data["text"] = f"[GEN_AI with prompt='{prompt}']: " + data["text"]
        elif node.node_type == NodeType.FORMATTER:
            data["text"] = data["text"].upper()
        else:
            pass  # Skip unknown node types
    return {"final_output": data["text"]}
```

client/package.json

```json
{
  "name": "workflow-client",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "typescript": "^4.5.5",
    "vite": "^4.0.0",
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0"
  }
}
```

client/tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

client/vite.config.ts

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000
  }
})
```

client/src/type.tsx

```ts
export interface Workflow {
  id: string;
  name: string;
  nodes: Node[];
}

export interface Node {
  id: string;
  node_type: NodeType;
  config: Record<string, unknown>;
}

export type NodeType = "extract_text" | "generative_ai" | "formatter";

export interface CreateWorkflowRequest {
  name: string;
}

export interface CreateWorkflowResponse {
  id: string;
  name: string;
}
```

client/src/api.ts

```ts
import axios from 'axios';
import { CreateWorkflowRequest, CreateWorkflowResponse, Workflow, NodeType } from './types';

const API_BASE = "<http://localhost:8000>";

export async function createWorkflow(req: CreateWorkflowRequest): Promise<CreateWorkflowResponse> {
  const res = await axios.post(`${API_BASE}/workflows`, req);
  return res.data;
}

export async function getWorkflow(wfId: string): Promise<Workflow> {
  const res = await axios.get(`${API_BASE}/workflows/${wfId}`);
  return res.data;
}

export async function addNode(wfId: string, nodeType: NodeType, config: Record<string, any>) {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/nodes`, { node_type: nodeType, config });
  return res.data;
}

export async function runWorkflow(wfId: string) {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/run`);
  return res.data;
}
```

client/src/components/App.tsx

```ts
import React, { useState } from 'react';
import { createWorkflow, getWorkflow, addNode, runWorkflow } from './api';
import { Workflow } from './types';

function App() {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [workflowName, setWorkflowName] = useState("");

  async function handleCreateWorkflow() {
    if (!workflowName) return;
    const result = await createWorkflow({ name: workflowName });
    setWorkflowId(result.id);
    setWorkflow(null);
  }

  async function handleFetchWorkflow() {
    if (!workflowId) return;
    const wf = await getWorkflow(workflowId);
    setWorkflow(wf);
  }

  async function handleAddNode(nodeType: string) {
    if (!workflowId) return;
    await addNode(workflowId, nodeType as any, { prompt: "Summarize this doc" });
    handleFetchWorkflow();
  }

  async function handleRunWorkflow() {
    if (!workflowId) return;
    const result = await runWorkflow(workflowId);
    alert("Final output: " + result.final_output);
  }

  return (
    <div style={{ margin: '20px' }}>
      <h1>Workflow Editor (Sample)</h1>
      <div>
        <input 
          type="text" 
          placeholder="Workflow name" 
          value={workflowName} 
          onChange={e => setWorkflowName(e.target.value)} 
        />
        <button onClick={handleCreateWorkflow}>Create Workflow</button>
      </div>

      {workflowId && (
        <>
          <p>Current Workflow ID: {workflowId}</p>
          <button onClick={handleFetchWorkflow}>Fetch Workflow</button>
        </>
      )}

      {workflow && (
        <div style={{ marginTop: '10px' }}>
          <h2>{workflow.name} (ID: {workflow.id})</h2>
          <ul>
            {workflow.nodes.map(n => (
              <li key={n.id}>
                {n.node_type} | {JSON.stringify(n.config)}
              </li>
            ))}
          </ul>
          <div>
            <button onClick={() => handleAddNode("extract_text")}>Add Extract Node</button>
            <button onClick={() => handleAddNode("generative_ai")}>Add AI Node</button>
            <button onClick={() => handleAddNode("formatter")}>Add Formatter Node</button>
          </div>
          <button onClick={handleRunWorkflow} style={{ marginTop: '10px' }}>Run Workflow</button>
        </div>
      )}
    </div>
  );
}

export default App;
```