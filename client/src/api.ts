import axios from 'axios';
import {
  CreateWorkflowRequest,
  CreateWorkflowResponse,
  Workflow,
  NodeType,
  JobAccepted,
  Job,
  FileUploadResponse,
  RunsResponse,
  AddNodeRequest,
  AddNodeResponse,
  AddEdgeRequest,
  AddEdgeResponse,
  WorkflowEdgesResponse
} from './types';

const API_BASE = (typeof import.meta !== 'undefined' && (import.meta as any).env && (import.meta as any).env.VITE_API_BASE)
  ? (import.meta as any).env.VITE_API_BASE
  : 'http://localhost:8000';

export async function createWorkflow(req: CreateWorkflowRequest): Promise<CreateWorkflowResponse> {
  const res = await axios.post(`${API_BASE}/workflows`, req);
  return res.data;
}

export async function getWorkflow(wfId: string): Promise<Workflow> {
  const res = await axios.get(`${API_BASE}/workflows/${wfId}`);
  return res.data;
}

export async function addNode(wfId: string, nodeType: NodeType, config: Record<string, any>): Promise<AddNodeResponse> {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/nodes`, { node_type: nodeType, config });
  return res.data;
}

// Updated for async execution
export async function runWorkflowAsync(wfId: string): Promise<JobAccepted> {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/run`);
  return res.data;
}

// Legacy sync method for backward compatibility
export async function runWorkflow(wfId: string): Promise<JobAccepted> {
  return runWorkflowAsync(wfId);
}

// New API methods for async job handling
export async function getJob(jobId: string): Promise<Job> {
  const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
  return res.data;
}

export async function getRuns(wfId: string): Promise<RunsResponse> {
  const res = await axios.get(`${API_BASE}/workflows/${wfId}/runs`);
  return res.data;
}

// File upload method
export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await axios.post(`${API_BASE}/files`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
}

// Utility method to poll job status until completion
export async function pollJobUntilComplete(jobId: string, maxPolls: number = 30, pollInterval: number = 1000): Promise<Job> {
  for (let i = 0; i < maxPolls; i++) {
    const job = await getJob(jobId);

    if (job.status === 'Succeeded' || job.status === 'Failed') {
      return job;
    }

    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  throw new Error(`Job ${jobId} did not complete within ${maxPolls} polls`);
}

// Edge API functions for DAG workflows
export async function addEdge(wfId: string, req: AddEdgeRequest): Promise<AddEdgeResponse> {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/edges`, req);
  return res.data;
}

export async function getEdges(wfId: string): Promise<WorkflowEdgesResponse> {
  const res = await axios.get(`${API_BASE}/workflows/${wfId}/edges`);
  return res.data;
}



