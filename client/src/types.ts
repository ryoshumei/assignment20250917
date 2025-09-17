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



