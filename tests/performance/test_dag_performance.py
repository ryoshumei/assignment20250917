import pytest
import time
import asyncio
from unittest.mock import patch, AsyncMock
from server.services.graph_service import topo_schedule, validate_edges_no_cycles
from server.services.job_service import JobService
from server.db_models import NodeDB, EdgeDB


class MockNode:
    """Mock node for performance testing"""
    def __init__(self, node_id: str):
        self.id = node_id


class MockEdge:
    """Mock edge for performance testing"""
    def __init__(self, from_node_id: str, to_node_id: str):
        self.workflow_id = "perf-test"
        self.from_node_id = from_node_id
        self.from_port = "output"
        self.to_node_id = to_node_id
        self.to_port = "input"
        self.condition = None


def create_linear_dag(size: int):
    """Create a linear DAG: N1 -> N2 -> N3 -> ... -> Nn"""
    nodes = [MockNode(f"N{i}") for i in range(1, size + 1)]
    edges = [MockEdge(f"N{i}", f"N{i+1}") for i in range(1, size)]
    return nodes, edges


def create_diamond_dag(layers: int):
    """Create a diamond-shaped DAG with specified layers"""
    nodes = []
    edges = []

    # Create nodes
    for layer in range(layers):
        if layer == 0 or layer == layers - 1:
            # Start and end layers have 1 node
            nodes.append(MockNode(f"L{layer}N1"))
        else:
            # Middle layers have 2 nodes
            nodes.append(MockNode(f"L{layer}N1"))
            nodes.append(MockNode(f"L{layer}N2"))

    # Create edges
    for layer in range(layers - 1):
        if layer == 0:
            # From start to first diamond layer
            edges.append(MockEdge("L0N1", "L1N1"))
            edges.append(MockEdge("L0N1", "L1N2"))
        elif layer == layers - 2:
            # From last diamond layer to end
            edges.append(MockEdge(f"L{layer}N1", f"L{layer+1}N1"))
            edges.append(MockEdge(f"L{layer}N2", f"L{layer+1}N1"))
        else:
            # Between diamond layers (full connectivity)
            for from_n in range(1, 3):
                for to_n in range(1, 3):
                    edges.append(MockEdge(f"L{layer}N{from_n}", f"L{layer+1}N{to_n}"))

    return nodes, edges


def create_fan_out_dag(fan_factor: int):
    """Create fan-out DAG: 1 root -> fan_factor nodes -> 1 end"""
    nodes = [MockNode("ROOT")]
    edges = []

    # Fan-out nodes
    for i in range(fan_factor):
        node_id = f"FAN{i}"
        nodes.append(MockNode(node_id))
        edges.append(MockEdge("ROOT", node_id))

    # End node
    nodes.append(MockNode("END"))
    for i in range(fan_factor):
        edges.append(MockEdge(f"FAN{i}", "END"))

    return nodes, edges


class TestDAGPerformance:
    """Performance tests for DAG operations"""

    def test_cycle_detection_linear_performance(self):
        """Test cycle detection performance on linear DAGs"""
        sizes = [10, 50, 100, 500]
        times = []

        for size in sizes:
            nodes, edges = create_linear_dag(size)

            start_time = time.perf_counter()
            validate_edges_no_cycles("perf-test", edges, nodes)
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            times.append(execution_time)

            # Should complete quickly even for large graphs
            assert execution_time < 1.0, f"Cycle detection too slow for {size} nodes: {execution_time:.3f}s"

        print(f"\nCycle Detection Performance (Linear DAG):")
        for size, exec_time in zip(sizes, times):
            print(f"  {size:3d} nodes: {exec_time:.3f}s")

        # Should scale reasonably (not exponentially)
        if len(times) >= 2:
            scaling_factor = times[-1] / times[0]
            size_factor = sizes[-1] / sizes[0]
            assert scaling_factor < size_factor * 2, f"Poor scaling: {scaling_factor:.2f}x time for {size_factor}x size"

    def test_cycle_detection_diamond_performance(self):
        """Test cycle detection performance on diamond DAGs"""
        layer_counts = [3, 5, 7, 10]
        times = []

        for layers in layer_counts:
            nodes, edges = create_diamond_dag(layers)

            start_time = time.perf_counter()
            validate_edges_no_cycles("perf-test", edges, nodes)
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            times.append(execution_time)

            # Should complete quickly even for complex graphs
            assert execution_time < 2.0, f"Cycle detection too slow for {layers} layers: {execution_time:.3f}s"

        print(f"\nCycle Detection Performance (Diamond DAG):")
        for layers, exec_time in zip(layer_counts, times):
            print(f"  {layers:2d} layers: {exec_time:.3f}s")

    def test_topological_scheduling_performance(self):
        """Test topological scheduling performance"""
        sizes = [10, 50, 100, 200]
        times = []

        for size in sizes:
            nodes, edges = create_linear_dag(size)

            start_time = time.perf_counter()
            batches = list(topo_schedule(edges, nodes))
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            times.append(execution_time)

            # Verify correctness
            assert len(batches) == size  # Linear chain should have n batches

            # Should complete quickly
            assert execution_time < 1.0, f"Topological scheduling too slow for {size} nodes: {execution_time:.3f}s"

        print(f"\nTopological Scheduling Performance:")
        for size, exec_time in zip(sizes, times):
            print(f"  {size:3d} nodes: {exec_time:.3f}s")

    def test_fan_out_scheduling_performance(self):
        """Test performance with high fan-out DAGs"""
        fan_factors = [5, 20, 50, 100]
        times = []

        for fan_factor in fan_factors:
            nodes, edges = create_fan_out_dag(fan_factor)

            start_time = time.perf_counter()
            batches = list(topo_schedule(edges, nodes))
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            times.append(execution_time)

            # Verify correctness: should have 3 batches (root, fan-out nodes, end)
            assert len(batches) == 3
            assert len(batches[1]) == fan_factor  # Middle batch should have all fan-out nodes

            # Should handle high parallelism efficiently
            assert execution_time < 1.0, f"Fan-out scheduling too slow for {fan_factor} parallel: {execution_time:.3f}s"

        print(f"\nFan-out Scheduling Performance:")
        for fan_factor, exec_time in zip(fan_factors, times):
            print(f"  {fan_factor:3d} parallel: {exec_time:.3f}s")

    def test_memory_usage_large_dag(self):
        """Test memory efficiency with large DAGs"""
        # Create a moderately large DAG
        nodes, edges = create_diamond_dag(8)  # ~15 nodes, ~32 edges

        # Measure memory indirectly by ensuring operations complete
        start_time = time.perf_counter()

        # Multiple operations to stress test
        for _ in range(100):
            validate_edges_no_cycles("perf-test", edges, nodes)
            list(topo_schedule(edges, nodes))

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Should handle repeated operations efficiently
        assert execution_time < 5.0, f"Memory/efficiency issue: {execution_time:.3f}s for 100 iterations"

        print(f"\nMemory Efficiency Test:")
        print(f"  100 iterations on 8-layer diamond: {execution_time:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_dag_operations(self):
        """Test performance under concurrent DAG operations"""
        nodes, edges = create_fan_out_dag(20)

        async def dag_operation():
            """Simulate concurrent DAG operations"""
            validate_edges_no_cycles("perf-test", edges, nodes)
            return list(topo_schedule(edges, nodes))

        # Run multiple concurrent operations
        start_time = time.perf_counter()

        tasks = [dag_operation() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Verify all operations completed correctly
        assert len(results) == 10
        for result in results:
            assert len(result) == 3  # Fan-out DAG should have 3 batches

        # Should handle concurrency efficiently
        assert execution_time < 2.0, f"Concurrent operations too slow: {execution_time:.3f}s"

        print(f"\nConcurrent Operations Test:")
        print(f"  10 concurrent DAG operations: {execution_time:.3f}s")

    def test_edge_case_performance(self):
        """Test performance on edge cases"""
        test_cases = [
            ("empty_graph", [], []),
            ("single_node", [MockNode("SINGLE")], []),
            ("disconnected_nodes", [MockNode("A"), MockNode("B")], []),
        ]

        print(f"\nEdge Case Performance:")

        for case_name, nodes, edges in test_cases:
            start_time = time.perf_counter()

            # Should handle edge cases gracefully
            validate_edges_no_cycles("perf-test", edges, nodes)
            batches = list(topo_schedule(edges, nodes))

            end_time = time.perf_counter()
            execution_time = end_time - start_time

            # Should be nearly instantaneous
            assert execution_time < 0.1, f"Edge case {case_name} too slow: {execution_time:.3f}s"

            print(f"  {case_name:15s}: {execution_time:.3f}s")

    def test_worst_case_cycle_detection(self):
        """Test cycle detection on worst-case scenarios"""
        # Create a cycle at the end of a long chain
        nodes = [MockNode(f"N{i}") for i in range(1, 101)]  # 100 nodes
        edges = [MockEdge(f"N{i}", f"N{i+1}") for i in range(1, 100)]  # Linear chain
        edges.append(MockEdge("N100", "N1"))  # Add cycle

        start_time = time.perf_counter()

        with pytest.raises(Exception):  # Should detect the cycle
            validate_edges_no_cycles("perf-test", edges, nodes)

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Should detect cycle quickly even in worst case
        assert execution_time < 2.0, f"Worst-case cycle detection too slow: {execution_time:.3f}s"

        print(f"\nWorst-case Cycle Detection:")
        print(f"  100-node chain with cycle: {execution_time:.3f}s")

    def test_performance_regression_benchmark(self):
        """Benchmark test for performance regression detection"""
        # Standard benchmark: 50-node linear DAG
        nodes, edges = create_linear_dag(50)

        # Run multiple iterations for stable timing
        times = []
        for _ in range(20):
            start_time = time.perf_counter()

            validate_edges_no_cycles("perf-test", edges, nodes)
            list(topo_schedule(edges, nodes))

            end_time = time.perf_counter()
            times.append(end_time - start_time)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Performance benchmarks for regression detection
        assert avg_time < 0.1, f"Average performance regression: {avg_time:.3f}s > 0.1s"
        assert max_time < 0.2, f"Max performance regression: {max_time:.3f}s > 0.2s"

        print(f"\nPerformance Benchmark (50-node linear DAG):")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Maximum time: {max_time:.3f}s")
        print(f"  Iterations: {len(times)}")