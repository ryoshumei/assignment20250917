import pytest
from server.services.graph_service import (
    validate_edges_no_cycles,
    topo_schedule,
    get_node_dependencies,
    aggregate_inputs
)
from server.db_models import EdgeDB, NodeDB


class MockNode:
    """Mock node for testing"""
    def __init__(self, node_id: str):
        self.id = node_id


class MockEdge:
    """Mock edge for testing"""
    def __init__(self, from_node_id: str, to_node_id: str, from_port: str = "output", to_port: str = "input"):
        self.workflow_id = "test-workflow"
        self.from_node_id = from_node_id
        self.from_port = from_port
        self.to_node_id = to_node_id
        self.to_port = to_port
        self.condition = None


class TestCycleDetection:
    """Unit tests for cycle detection in DAG validation"""

    def test_validate_edges_no_cycles_valid_dag(self):
        """Test cycle detection with valid DAG"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C")]
        edges = [
            MockEdge("A", "B"),
            MockEdge("B", "C")
        ]

        # Should not raise exception
        validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_simple_cycle(self):
        """Test cycle detection with simple cycle"""
        nodes = [MockNode("A"), MockNode("B")]
        edges = [
            MockEdge("A", "B"),
            MockEdge("B", "A")  # Creates cycle
        ]

        with pytest.raises(Exception, match="Cycle detected"):
            validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_self_loop(self):
        """Test cycle detection with self-loop"""
        nodes = [MockNode("A")]
        edges = [
            MockEdge("A", "A")  # Self-loop
        ]

        with pytest.raises(Exception, match="Cycle detected"):
            validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_complex_cycle(self):
        """Test cycle detection with complex cycle A->B->C->A"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C")]
        edges = [
            MockEdge("A", "B"),
            MockEdge("B", "C"),
            MockEdge("C", "A")  # Creates cycle
        ]

        with pytest.raises(Exception, match="Cycle detected"):
            validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_diamond_pattern(self):
        """Test cycle detection with diamond pattern (valid DAG)"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C"), MockNode("D")]
        edges = [
            MockEdge("A", "B"),
            MockEdge("A", "C"),
            MockEdge("B", "D"),
            MockEdge("C", "D")
        ]

        # Should not raise exception
        validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_invalid_node_reference(self):
        """Test validation with invalid node references"""
        nodes = [MockNode("A"), MockNode("B")]
        edges = [
            MockEdge("A", "NONEXISTENT")  # Invalid node reference
        ]

        with pytest.raises(Exception, match="Edge references invalid to_node_id"):
            validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_empty_graph(self):
        """Test validation with empty graph"""
        nodes = []
        edges = []

        # Should not raise exception
        validate_edges_no_cycles("test-workflow", edges, nodes)

    def test_validate_edges_no_cycles_disconnected_components(self):
        """Test validation with disconnected components"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C"), MockNode("D")]
        edges = [
            MockEdge("A", "B"),  # Component 1
            MockEdge("C", "D")   # Component 2 (disconnected)
        ]

        # Should not raise exception
        validate_edges_no_cycles("test-workflow", edges, nodes)


class TestTopologicalScheduling:
    """Unit tests for topological scheduling"""

    def test_topo_schedule_linear_chain(self):
        """Test topological scheduling with linear chain A->B->C"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C")]
        edges = [
            MockEdge("A", "B"),
            MockEdge("B", "C")
        ]

        batches = list(topo_schedule(edges, nodes))

        assert len(batches) == 3
        assert batches[0] == ["A"]  # No dependencies
        assert batches[1] == ["B"]  # Depends on A
        assert batches[2] == ["C"]  # Depends on B

    def test_topo_schedule_diamond_pattern(self):
        """Test topological scheduling with diamond pattern"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C"), MockNode("D")]
        edges = [
            MockEdge("A", "B"),
            MockEdge("A", "C"),
            MockEdge("B", "D"),
            MockEdge("C", "D")
        ]

        batches = list(topo_schedule(edges, nodes))

        assert len(batches) == 3
        assert batches[0] == ["A"]  # No dependencies
        assert set(batches[1]) == {"B", "C"}  # Both depend only on A (parallel)
        assert batches[2] == ["D"]  # Depends on both B and C

    def test_topo_schedule_no_edges(self):
        """Test topological scheduling with no edges (all parallel)"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C")]
        edges = []

        batches = list(topo_schedule(edges, nodes))

        assert len(batches) == 1
        assert set(batches[0]) == {"A", "B", "C"}  # All can run in parallel

    def test_topo_schedule_single_node(self):
        """Test topological scheduling with single node"""
        nodes = [MockNode("A")]
        edges = []

        batches = list(topo_schedule(edges, nodes))

        assert len(batches) == 1
        assert batches[0] == ["A"]

    def test_topo_schedule_fan_out_fan_in(self):
        """Test topological scheduling with fan-out/fan-in pattern"""
        nodes = [MockNode("A"), MockNode("B"), MockNode("C"), MockNode("D"), MockNode("E")]
        edges = [
            MockEdge("A", "B"),  # A fans out to B, C, D
            MockEdge("A", "C"),
            MockEdge("A", "D"),
            MockEdge("B", "E"),  # B, C, D fan in to E
            MockEdge("C", "E"),
            MockEdge("D", "E")
        ]

        batches = list(topo_schedule(edges, nodes))

        assert len(batches) == 3
        assert batches[0] == ["A"]
        assert set(batches[1]) == {"B", "C", "D"}  # Parallel execution
        assert batches[2] == ["E"]

    def test_topo_schedule_complex_dag(self):
        """Test topological scheduling with complex DAG"""
        nodes = [MockNode(f"N{i}") for i in range(1, 7)]  # N1 through N6
        edges = [
            MockEdge("N1", "N2"),
            MockEdge("N1", "N3"),
            MockEdge("N2", "N4"),
            MockEdge("N3", "N4"),
            MockEdge("N3", "N5"),
            MockEdge("N4", "N6"),
            MockEdge("N5", "N6")
        ]

        batches = list(topo_schedule(edges, nodes))

        assert len(batches) == 4
        assert batches[0] == ["N1"]
        assert set(batches[1]) == {"N2", "N3"}
        assert set(batches[2]) == {"N4", "N5"}
        assert batches[3] == ["N6"]


class TestNodeDependencies:
    """Unit tests for node dependency resolution"""

    def test_get_node_dependencies_no_dependencies(self):
        """Test getting dependencies for node with no dependencies"""
        edges = [
            MockEdge("A", "B"),
            MockEdge("B", "C")
        ]

        deps = get_node_dependencies("A", edges)
        assert deps == []

    def test_get_node_dependencies_single_dependency(self):
        """Test getting dependencies for node with single dependency"""
        edges = [
            MockEdge("A", "B"),
            MockEdge("B", "C")
        ]

        deps = get_node_dependencies("B", edges)
        assert deps == ["A"]

    def test_get_node_dependencies_multiple_dependencies(self):
        """Test getting dependencies for node with multiple dependencies"""
        edges = [
            MockEdge("A", "C"),
            MockEdge("B", "C")
        ]

        deps = get_node_dependencies("C", edges)
        assert set(deps) == {"A", "B"}

    def test_get_node_dependencies_complex_graph(self):
        """Test getting dependencies in complex graph"""
        edges = [
            MockEdge("A", "B"),
            MockEdge("A", "C"),
            MockEdge("B", "D"),
            MockEdge("C", "D"),
            MockEdge("E", "D")  # Additional dependency
        ]

        deps = get_node_dependencies("D", edges)
        assert set(deps) == {"B", "C", "E"}


class TestInputAggregation:
    """Unit tests for input aggregation (AND-join semantics)"""

    def test_aggregate_inputs_no_dependencies(self):
        """Test input aggregation with no dependencies"""
        dependencies = []
        node_outputs = {"A": "output A", "B": "output B"}

        result = aggregate_inputs(dependencies, node_outputs)
        assert result == ""

    def test_aggregate_inputs_single_dependency(self):
        """Test input aggregation with single dependency"""
        dependencies = ["A"]
        node_outputs = {"A": "output from A", "B": "output from B"}

        result = aggregate_inputs(dependencies, node_outputs)
        assert result == "output from A"

    def test_aggregate_inputs_multiple_dependencies(self):
        """Test input aggregation with multiple dependencies (AND-join)"""
        dependencies = ["A", "B"]
        node_outputs = {
            "A": "output from node A",
            "B": "output from node B",
            "C": "output from node C"
        }

        result = aggregate_inputs(dependencies, node_outputs)

        # Should contain outputs from both A and B, joined
        assert "output from node A" in result
        assert "output from node B" in result
        assert "\n\n" in result  # Default separator

    def test_aggregate_inputs_missing_dependency_output(self):
        """Test input aggregation with missing dependency output"""
        dependencies = ["A", "B"]
        node_outputs = {"A": "output from A"}  # Missing B

        result = aggregate_inputs(dependencies, node_outputs)

        # Should handle missing output gracefully
        assert "output from A" in result

    def test_aggregate_inputs_empty_outputs(self):
        """Test input aggregation with empty outputs"""
        dependencies = ["A", "B"]
        node_outputs = {"A": "", "B": ""}

        result = aggregate_inputs(dependencies, node_outputs)

        # Should handle empty outputs
        assert isinstance(result, str)

    def test_aggregate_inputs_deterministic_order(self):
        """Test that input aggregation produces deterministic order"""
        dependencies = ["B", "A", "C"]  # Intentionally unordered
        node_outputs = {
            "A": "A output",
            "B": "B output",
            "C": "C output"
        }

        result1 = aggregate_inputs(dependencies, node_outputs)
        result2 = aggregate_inputs(dependencies, node_outputs)

        # Should be deterministic
        assert result1 == result2

        # Should sort alphabetically for determinism
        a_pos = result1.find("A output")
        b_pos = result1.find("B output")
        c_pos = result1.find("C output")

        # Should maintain alphabetical order (A, B, C)
        assert a_pos < b_pos < c_pos