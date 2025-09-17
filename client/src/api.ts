import axios from 'axios';
import { CreateWorkflowRequest, CreateWorkflowResponse, Workflow, NodeType } from './types';

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

export async function addNode(wfId: string, nodeType: NodeType, config: Record<string, any>) {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/nodes`, { node_type: nodeType, config });
  return res.data;
}

export async function runWorkflow(wfId: string) {
  const res = await axios.post(`${API_BASE}/workflows/${wfId}/run`);
  return res.data;
}



