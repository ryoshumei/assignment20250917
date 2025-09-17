import React, { useState, useEffect } from 'react';
import {
  createWorkflow,
  getWorkflow,
  addNode,
  runWorkflowAsync,
  uploadFile,
  getJob,
  getRuns,
  pollJobUntilComplete
} from './api';
import { Workflow, JobStatus, Job, NodeType } from './types';

function App() {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [workflowName, setWorkflowName] = useState("");
  const [uploadedFileId, setUploadedFileId] = useState<string | null>(null);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [runs, setRuns] = useState<Job[]>([]);
  const [isPolling, setIsPolling] = useState(false);

  // Node configuration states
  const [llmModel, setLlmModel] = useState("gpt-4.1-mini");
  const [llmPrompt, setLlmPrompt] = useState("Summarize the following text: {text}");
  const [llmTemperature, setLlmTemperature] = useState(0.7);
  const [formatterRules, setFormatterRules] = useState<string[]>(["lowercase"]);

  async function handleCreateWorkflow() {
    if (!workflowName) return;
    const result = await createWorkflow({ name: workflowName });
    setWorkflowId(result.id);
    setWorkflow(null);
    setCurrentJob(null);
    setRuns([]);
    // Auto-fetch the newly created workflow
    setTimeout(() => {
      handleFetchWorkflow();
    }, 100);
  }

  async function handleFetchWorkflow() {
    if (!workflowId) return;
    try {
      const wf = await getWorkflow(workflowId);
      setWorkflow(wf);
    } catch (error) {
      console.error('Failed to fetch workflow:', error);
      alert(`Failed to fetch workflow: ${error}`);
    }
  }

  async function handleFetchRuns() {
    if (!workflowId) return;
    try {
      const runsResponse = await getRuns(workflowId);
      setRuns(runsResponse.runs);
    } catch (error) {
      console.error('Failed to fetch runs:', error);
      alert(`Failed to fetch runs: ${error}`);
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const result = await uploadFile(file);
      setUploadedFileId(result.file_id);
      alert(`File uploaded successfully: ${result.filename}`);
    } catch (error) {
      alert(`Upload failed: ${error}`);
    }
  }

  async function handleAddExtractTextNode() {
    if (!workflowId || !uploadedFileId) {
      alert("Please upload a PDF file first");
      return;
    }
    await addNode(workflowId, "extract_text", { file_id: uploadedFileId });
    handleFetchWorkflow();
  }

  async function handleAddGenerativeAINode() {
    if (!workflowId) return;
    await addNode(workflowId, "generative_ai", {
      model: llmModel,
      prompt: llmPrompt,
      temperature: llmTemperature,
    });
    handleFetchWorkflow();
  }

  async function handleAddFormatterNode() {
    if (!workflowId) return;
    await addNode(workflowId, "formatter", {
      rules: formatterRules,
    });
    handleFetchWorkflow();
  }

  async function handleRunWorkflow() {
    if (!workflowId) return;

    try {
      const jobResponse = await runWorkflowAsync(workflowId);
      setCurrentJob({
        id: jobResponse.job_id,
        workflow_id: workflowId,
        status: JobStatus.Pending,
        started_at: new Date().toISOString(),
      });

      setIsPolling(true);

      // Poll for completion
      const completedJob = await pollJobUntilComplete(jobResponse.job_id);
      setCurrentJob(completedJob);
      setIsPolling(false);

      // Refresh runs list
      handleFetchRuns();

      if (completedJob.status === 'Succeeded') {
        alert(`Workflow completed!\nOutput: ${completedJob.final_output}`);
      } else {
        alert(`Workflow failed: ${completedJob.error_message}`);
      }
    } catch (error) {
      setIsPolling(false);
      alert(`Error running workflow: ${error}`);
    }
  }

  function toggleFormatterRule(rule: string) {
    if (formatterRules.includes(rule)) {
      setFormatterRules(formatterRules.filter(r => r !== rule));
    } else {
      setFormatterRules([...formatterRules, rule]);
    }
  }

  // Auto-refresh workflow and runs when workflow changes
  useEffect(() => {
    if (workflowId) {
      handleFetchWorkflow();
      handleFetchRuns();
    }
  }, [workflowId]);

  // Define handleFetchWorkflow and handleFetchRuns with useCallback to prevent infinite loops
  const handleFetchWorkflowCallback = React.useCallback(async () => {
    if (!workflowId) return;
    try {
      const wf = await getWorkflow(workflowId);
      setWorkflow(wf);
    } catch (error) {
      console.error('Failed to fetch workflow:', error);
      alert(`Failed to fetch workflow: ${error}`);
    }
  }, [workflowId]);

  const handleFetchRunsCallback = React.useCallback(async () => {
    if (!workflowId) return;
    try {
      const runsResponse = await getRuns(workflowId);
      setRuns(runsResponse.runs);
    } catch (error) {
      console.error('Failed to fetch runs:', error);
      alert(`Failed to fetch runs: ${error}`);
    }
  }, [workflowId]);

  return (
    <div style={{ margin: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>🔄 Async Workflow Editor</h1>

      {/* Workflow Creation */}
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
        <h3>Create New Workflow</h3>
        <input
          type="text"
          placeholder="Workflow name"
          value={workflowName}
          onChange={e => setWorkflowName(e.target.value)}
          style={{ marginRight: '10px', padding: '8px' }}
        />
        <button onClick={handleCreateWorkflow} style={{ padding: '8px 16px' }}>
          Create Workflow
        </button>
      </div>

      {/* File Upload Section */}
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
        <h3>📄 PDF File Upload</h3>
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileUpload}
          style={{ marginRight: '10px' }}
        />
        {uploadedFileId && (
          <span style={{ color: 'green' }}>✅ File uploaded (ID: {uploadedFileId})</span>
        )}
      </div>

      {workflowId && (
        <>
          <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
            <h3>Current Workflow</h3>
            <p><strong>ID:</strong> {workflowId}</p>
            <button onClick={handleFetchWorkflow} style={{ marginRight: '10px', padding: '8px 16px' }}>
              Refresh Workflow
            </button>
            <button onClick={handleFetchRuns} style={{ padding: '8px 16px' }}>
              Refresh Runs
            </button>
          </div>
        </>
      )}

      {workflow && (
        <div style={{ marginBottom: '20px' }}>
          {/* Current Nodes */}
          <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px', marginBottom: '15px' }}>
            <h3>🔗 {workflow.name} - Current Nodes</h3>
            {workflow.nodes.length === 0 ? (
              <p style={{ color: '#666' }}>No nodes added yet</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {workflow.nodes.map((n, index) => (
                  <li key={n.id} style={{
                    padding: '8px',
                    margin: '5px 0',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '3px'
                  }}>
                    <strong>{index + 1}. {n.node_type.toUpperCase()}</strong>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      Config: {JSON.stringify(n.config, null, 2)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Node Configuration and Addition */}
          <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px', marginBottom: '15px' }}>
            <h3>➕ Add Nodes</h3>

            {/* Extract Text Node */}
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '5px' }}>
              <h4>📄 Extract Text Node</h4>
              <button
                onClick={handleAddExtractTextNode}
                disabled={!uploadedFileId}
                style={{
                  padding: '8px 16px',
                  backgroundColor: uploadedFileId ? '#4CAF50' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px'
                }}
              >
                Add Extract Text Node
              </button>
              {!uploadedFileId && <p style={{ color: '#666', fontSize: '12px' }}>Upload a PDF file first</p>}
            </div>

            {/* Generative AI Node */}
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '5px' }}>
              <h4>🤖 Generative AI Node</h4>
              <div style={{ marginBottom: '10px' }}>
                <label>Model: </label>
                <select value={llmModel} onChange={e => setLlmModel(e.target.value)} style={{ marginLeft: '5px', padding: '4px' }}>
                  <option value="gpt-4.1-mini">GPT-4.1 Mini</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="gpt-5">GPT-5</option>
                </select>
              </div>
              <div style={{ marginBottom: '10px' }}>
                <label>Prompt: </label>
                <textarea
                  value={llmPrompt}
                  onChange={e => setLlmPrompt(e.target.value)}
                  style={{ width: '100%', minHeight: '60px', padding: '5px' }}
                  placeholder="Use {text} as placeholder for input text"
                />
              </div>
              <div style={{ marginBottom: '10px' }}>
                <label>Temperature: </label>
                <input
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={llmTemperature}
                  onChange={e => setLlmTemperature(parseFloat(e.target.value))}
                  style={{ marginLeft: '5px', padding: '4px', width: '60px' }}
                />
              </div>
              <button
                onClick={handleAddGenerativeAINode}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px'
                }}
              >
                Add AI Node
              </button>
            </div>

            {/* Formatter Node */}
            <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '5px' }}>
              <h4>🎨 Formatter Node</h4>
              <div style={{ marginBottom: '10px' }}>
                <label>Rules (applied in order):</label>
                <div style={{ marginTop: '5px' }}>
                  {['lowercase', 'uppercase', 'full_to_half', 'half_to_full'].map(rule => (
                    <label key={rule} style={{ display: 'block', marginBottom: '5px' }}>
                      <input
                        type="checkbox"
                        checked={formatterRules.includes(rule)}
                        onChange={() => toggleFormatterRule(rule)}
                        style={{ marginRight: '8px' }}
                      />
                      {rule}
                    </label>
                  ))}
                </div>
                <p style={{ fontSize: '12px', color: '#666' }}>
                  Selected: [{formatterRules.join(', ')}]
                </p>
              </div>
              <button
                onClick={handleAddFormatterNode}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#FF9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px'
                }}
              >
                Add Formatter Node
              </button>
            </div>
          </div>

          {/* Run Workflow */}
          <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px', marginBottom: '15px' }}>
            <h3>▶️ Execute Workflow</h3>
            <button
              onClick={handleRunWorkflow}
              disabled={isPolling || workflow.nodes.length === 0}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                backgroundColor: isPolling ? '#ccc' : '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '5px'
              }}
            >
              {isPolling ? '⏳ Running...' : '▶️ Run Workflow Async'}
            </button>
            {workflow.nodes.length === 0 && (
              <p style={{ color: '#666', fontSize: '12px' }}>Add at least one node to run the workflow</p>
            )}
          </div>

          {/* Current Job Status */}
          {currentJob && (
            <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px', marginBottom: '15px' }}>
              <h3>🔄 Current Job Status</h3>
              <p><strong>Job ID:</strong> {currentJob.id}</p>
              <p><strong>Status:</strong>
                <span style={{
                  color: currentJob.status === 'Succeeded' ? 'green' :
                        currentJob.status === 'Failed' ? 'red' :
                        currentJob.status === 'Running' ? 'orange' : 'blue'
                }}>
                  {currentJob.status}
                </span>
              </p>
              {currentJob.final_output && (
                <div>
                  <strong>Final Output:</strong>
                  <div style={{
                    padding: '10px',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '3px',
                    marginTop: '5px',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {currentJob.final_output}
                  </div>
                </div>
              )}
              {currentJob.error_message && (
                <div>
                  <strong>Error:</strong>
                  <div style={{
                    padding: '10px',
                    backgroundColor: '#ffebee',
                    borderRadius: '3px',
                    marginTop: '5px',
                    color: 'red'
                  }}>
                    {currentJob.error_message}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Job History */}
          {runs.length > 0 && (
            <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
              <h3>📋 Job History</h3>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {runs.map(job => (
                  <div key={job.id} style={{
                    padding: '8px',
                    margin: '5px 0',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '3px',
                    border: `1px solid ${
                      job.status === 'Succeeded' ? '#4CAF50' :
                      job.status === 'Failed' ? '#f44336' :
                      job.status === 'Running' ? '#FF9800' : '#2196F3'
                    }`
                  }}>
                    <div style={{ fontSize: '12px' }}>
                      <strong>{job.id}</strong> - {job.status}
                      <span style={{ float: 'right' }}>
                        {new Date(job.started_at).toLocaleString()}
                      </span>
                    </div>
                    {job.final_output && (
                      <div style={{ fontSize: '11px', color: '#666', marginTop: '3px' }}>
                        Output: {job.final_output.substring(0, 100)}
                        {job.final_output.length > 100 ? '...' : ''}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;



