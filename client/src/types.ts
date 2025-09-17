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

// Job and Status Types for Async Execution
export enum JobStatus {
  Pending = "Pending",
  Running = "Running",
  Succeeded = "Succeeded",
  Failed = "Failed"
}

export interface Job {
  id: string;
  workflow_id: string;
  status: JobStatus;
  started_at: string;
  finished_at?: string;
  error_message?: string;
  final_output?: string;
}

export interface JobAccepted {
  job_id: string;
  message: string;
}

// File Upload Types
export interface FileUploadResponse {
  file_id: string;
  filename: string;
  message: string;
}

// Node Configuration Types
export interface ExtractTextConfig {
  file_id: string;
}

export interface GenerativeAIConfig {
  model: string;
  prompt: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
}

export interface FormatterConfig {
  rules: string[];
}

// API Response Types
export interface RunsResponse {
  runs: Job[];
}

export interface AddNodeRequest {
  node_type: NodeType;
  config: ExtractTextConfig | GenerativeAIConfig | FormatterConfig;
}

export interface AddNodeResponse {
  node_id: string;
  message: string;
}



