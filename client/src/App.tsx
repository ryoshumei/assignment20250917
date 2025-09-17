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



