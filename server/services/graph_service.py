from typing import List, Dict, Set, Iterator, Tuple
from collections import defaultdict, deque
from ..db_models import EdgeDB, NodeDB


class CycleDetectionError(Exception):
    """Raised when a cycle is detected in the DAG"""
    pass


class InvalidNodeReferenceError(Exception):
    """Raised when an edge references a non-existent node"""
    pass


def validate_edges_no_cycles(workflow_id: str, edges: List[EdgeDB], nodes: List[NodeDB]) -> None:
    """
    Validate that edges form a DAG (no cycles) and reference valid nodes.

    Args:
        workflow_id: The workflow ID for context
        edges: List of edges to validate
        nodes: List of nodes that edges can reference

    Raises:
        CycleDetectionError: If a cycle is detected
        InvalidNodeReferenceError: If an edge references a non-existent node
    """
    # Build node ID set for validation
    node_ids = {node.id for node in nodes}

    # Validate all edge references
    for edge in edges:
        if edge.from_node_id not in node_ids:
            raise InvalidNodeReferenceError(f"Edge references invalid from_node_id: {edge.from_node_id}")
        if edge.to_node_id not in node_ids:
            raise InvalidNodeReferenceError(f"Edge references invalid to_node_id: {edge.to_node_id}")

    # Build adjacency graph
    graph = defaultdict(list)
    for edge in edges:
        graph[edge.from_node_id].append(edge.to_node_id)

    # DFS-based cycle detection
    white = set(node_ids)  # Not visited
    gray = set()          # Currently being processed
    black = set()         # Completely processed

    def dfs(node_id: str) -> None:
        if node_id in gray:
            raise CycleDetectionError(f"Cycle detected involving node: {node_id}")
        if node_id in black:
            return

        white.discard(node_id)
        gray.add(node_id)

        for neighbor in graph[node_id]:
            dfs(neighbor)

        gray.discard(node_id)
        black.add(node_id)

    # Check all nodes for cycles
    for node_id in list(white):
        if node_id in white:
            dfs(node_id)


def topo_schedule(edges: List[EdgeDB], nodes: List[NodeDB]) -> Iterator[List[str]]:
    """
    Generate topological schedule for DAG execution with AND-join semantics.

    Returns an iterator of node batches that can be executed in parallel.
    Each batch contains nodes that have no pending dependencies.

    Args:
        edges: List of edges defining dependencies
        nodes: List of nodes to schedule

    Yields:
        List[str]: Batch of node IDs ready for execution
    """
    # Build adjacency list and in-degree count
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    all_nodes = {node.id for node in nodes}

    # Initialize in-degree for all nodes
    for node_id in all_nodes:
        in_degree[node_id] = 0

    # Build graph and count in-degrees
    for edge in edges:
        graph[edge.from_node_id].append(edge.to_node_id)
        in_degree[edge.to_node_id] += 1

    # Find all nodes with no incoming edges (starting points)
    queue = deque([node_id for node_id in all_nodes if in_degree[node_id] == 0])

    while queue:
        # Process all nodes ready in this batch
        batch = []
        batch_size = len(queue)

        for _ in range(batch_size):
            node_id = queue.popleft()
            batch.append(node_id)

            # Reduce in-degree for all neighbors
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if batch:
            yield batch


def get_node_dependencies(node_id: str, edges: List[EdgeDB]) -> List[str]:
    """
    Get all direct dependencies (incoming nodes) for a given node.

    Args:
        node_id: The node to find dependencies for
        edges: List of edges

    Returns:
        List[str]: List of node IDs that this node depends on
    """
    return [edge.from_node_id for edge in edges if edge.to_node_id == node_id]


def aggregate_inputs(node_dependencies: List[str], node_outputs: Dict[str, str]) -> str:
    """
    Aggregate inputs from multiple upstream nodes using AND-join semantics.

    Args:
        node_dependencies: List of upstream node IDs
        node_outputs: Mapping of node_id -> output_text

    Returns:
        str: Aggregated input text
    """
    if not node_dependencies:
        return ""

    # Deterministic aggregation: join outputs with double newline
    inputs = []
    for dep_node_id in sorted(node_dependencies):  # Sort for determinism
        if dep_node_id in node_outputs:
            output = node_outputs[dep_node_id]
            if output:
                inputs.append(output)

    return "\n\n".join(inputs)