import pytest
from datetime import datetime
from server.models import NodeType
from server.schemas import (
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    AddNodeRequest,
    WorkflowDetailResponse,
    RunResponse,
    RunNodeResponse,
    WorkflowRunsResponse,
    RunDetailResponse
)


class TestNodeTypeEnum:
    """Test NodeType enum validation"""

    def test_valid_node_types(self):
        """Test all valid node type values"""
        assert NodeType.EXTRACT_TEXT == "extract_text"
        assert NodeType.GENERATIVE_AI == "generative_ai"
        assert NodeType.FORMATTER == "formatter"

    def test_node_type_values_list(self):
        """Test that all expected values are in the enum"""
        expected_values = {"extract_text", "generative_ai", "formatter"}
        actual_values = {item.value for item in NodeType}
        assert actual_values == expected_values


class TestRequestSchemas:
    """Test request schema validation"""

    def test_create_workflow_request_valid(self):
        """Test valid CreateWorkflowRequest"""
        data = {"name": "Test Workflow"}
        request = CreateWorkflowRequest(**data)
        assert request.name == "Test Workflow"

    def test_create_workflow_request_empty_name(self):
        """Test CreateWorkflowRequest with empty name (allowed in current schema)"""
        # Note: Current schema allows empty string, this test documents the behavior
        request = CreateWorkflowRequest(name="")
        assert request.name == ""

    def test_add_node_request_valid(self):
        """Test valid AddNodeRequest"""
        data = {
            "node_type": NodeType.EXTRACT_TEXT,
            "config": {"source": "document.pdf"}
        }
        request = AddNodeRequest(**data)
        assert request.node_type == NodeType.EXTRACT_TEXT
        assert request.config == {"source": "document.pdf"}

    def test_add_node_request_valid_node_types(self):
        """Test AddNodeRequest with all valid node types"""
        for node_type in NodeType:
            data = {"node_type": node_type, "config": {}}
            request = AddNodeRequest(**data)
            assert request.node_type == node_type

    def test_add_node_request_invalid_node_type(self):
        """Test AddNodeRequest with invalid node type fails"""
        with pytest.raises(ValueError):
            AddNodeRequest(node_type="invalid_type", config={})


class TestResponseSchemas:
    """Test response schema serialization"""

    def test_create_workflow_response(self):
        """Test CreateWorkflowResponse serialization"""
        data = {"id": "123", "name": "Test Workflow"}
        response = CreateWorkflowResponse(**data)
        assert response.id == "123"
        assert response.name == "Test Workflow"

    def test_workflow_detail_response(self):
        """Test WorkflowDetailResponse serialization"""
        data = {
            "id": "123",
            "name": "Test Workflow",
            "nodes": [
                {"id": "node1", "node_type": "extract_text", "config": {}},
                {"id": "node2", "node_type": "formatter", "config": {"format": "json"}}
            ]
        }
        response = WorkflowDetailResponse(**data)
        assert response.id == "123"
        assert response.name == "Test Workflow"
        assert len(response.nodes) == 2
        assert response.nodes[0]["node_type"] == "extract_text"

    def test_run_response_with_optional_fields(self):
        """Test RunResponse with all optional fields"""
        data = {
            "id": "run123",
            "workflow_id": "wf123",
            "status": "Succeeded",
            "started_at": datetime.utcnow(),
            "finished_at": datetime.utcnow(),
            "error_message": None,
            "final_output": "Final result"
        }
        response = RunResponse(**data)
        assert response.id == "run123"
        assert response.status == "Succeeded"
        assert response.final_output == "Final result"

    def test_run_response_minimal_fields(self):
        """Test RunResponse with only required fields"""
        data = {
            "id": "run123",
            "workflow_id": "wf123",
            "status": "Running",
            "started_at": datetime.utcnow()
        }
        response = RunResponse(**data)
        assert response.id == "run123"
        assert response.finished_at is None
        assert response.error_message is None
        assert response.final_output is None

    def test_run_node_response_complete(self):
        """Test RunNodeResponse with all fields"""
        data = {
            "id": "rn123",
            "run_id": "run123",
            "node_id": "node123",
            "node_type": "generative_ai",
            "status": "Succeeded",
            "started_at": datetime.utcnow(),
            "finished_at": datetime.utcnow(),
            "input_text": "Input data",
            "output_text": "Output data",
            "error_message": None
        }
        response = RunNodeResponse(**data)
        assert response.id == "rn123"
        assert response.node_type == "generative_ai"
        assert response.input_text == "Input data"
        assert response.output_text == "Output data"

    def test_run_node_response_with_null_node_id(self):
        """Test RunNodeResponse with null node_id (node deleted)"""
        data = {
            "id": "rn123",
            "run_id": "run123",
            "node_id": None,
            "node_type": "extract_text",
            "status": "Succeeded",
            "started_at": datetime.utcnow()
        }
        response = RunNodeResponse(**data)
        assert response.node_id is None
        assert response.node_type == "extract_text"


class TestCompositeSchemas:
    """Test composite schema structures"""

    def test_workflow_runs_response(self):
        """Test WorkflowRunsResponse with multiple runs"""
        runs_data = [
            {
                "id": "run1",
                "workflow_id": "wf123",
                "status": "Succeeded",
                "started_at": datetime.utcnow()
            },
            {
                "id": "run2",
                "workflow_id": "wf123",
                "status": "Failed",
                "started_at": datetime.utcnow(),
                "error_message": "Node failed"
            }
        ]
        runs = [RunResponse(**data) for data in runs_data]
        response = WorkflowRunsResponse(runs=runs)
        assert len(response.runs) == 2
        assert response.runs[0].status == "Succeeded"
        assert response.runs[1].status == "Failed"

    def test_run_detail_response(self):
        """Test RunDetailResponse with run and steps"""
        run_data = {
            "id": "run123",
            "workflow_id": "wf123",
            "status": "Succeeded",
            "started_at": datetime.utcnow()
        }
        steps_data = [
            {
                "id": "step1",
                "run_id": "run123",
                "node_type": "extract_text",
                "status": "Succeeded",
                "started_at": datetime.utcnow()
            },
            {
                "id": "step2",
                "run_id": "run123",
                "node_type": "formatter",
                "status": "Succeeded",
                "started_at": datetime.utcnow()
            }
        ]

        run = RunResponse(**run_data)
        steps = [RunNodeResponse(**data) for data in steps_data]
        response = RunDetailResponse(run=run, steps=steps)

        assert response.run.id == "run123"
        assert len(response.steps) == 2
        assert response.steps[0].node_type == "extract_text"
        assert response.steps[1].node_type == "formatter"


class TestValidationEdgeCases:
    """Test validation edge cases and error handling"""

    def test_run_status_validation(self):
        """Test that run status accepts expected values"""
        valid_statuses = ["Pending", "Running", "Succeeded", "Failed"]
        for status in valid_statuses:
            data = {
                "id": "run123",
                "workflow_id": "wf123",
                "status": status,
                "started_at": datetime.utcnow()
            }
            response = RunResponse(**data)
            assert response.status == status

    def test_run_node_status_validation(self):
        """Test that run node status accepts expected values"""
        valid_statuses = ["Pending", "Running", "Succeeded", "Failed"]
        for status in valid_statuses:
            data = {
                "id": "rn123",
                "run_id": "run123",
                "node_type": "extract_text",
                "status": status,
                "started_at": datetime.utcnow()
            }
            response = RunNodeResponse(**data)
            assert response.status == status

    def test_config_dict_flexibility(self):
        """Test that config field accepts various dictionary structures"""
        config_examples = [
            {},
            {"prompt": "test"},
            {"nested": {"key": "value"}},
            {"list": [1, 2, 3]},
            {"mixed": {"str": "value", "num": 42, "bool": True}}
        ]

        for config in config_examples:
            request = AddNodeRequest(node_type=NodeType.GENERATIVE_AI, config=config)
            assert request.config == config

    def test_datetime_serialization(self):
        """Test datetime field serialization"""
        test_time = datetime.utcnow()
        data = {
            "id": "run123",
            "workflow_id": "wf123",
            "status": "Running",
            "started_at": test_time
        }
        response = RunResponse(**data)
        assert response.started_at == test_time

        # Test serialization to dict
        response_dict = response.dict()
        assert "started_at" in response_dict