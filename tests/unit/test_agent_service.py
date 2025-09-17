import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from server.services.agent_service import validate_config, execute_agent_bounded


class TestAgentConfigValidation:
    """Unit tests for agent configuration validation"""

    def test_validate_config_valid(self):
        """Test valid agent configuration"""
        config = {
            "objective": "Process text efficiently",
            "tools": ["llm_call", "formatter"],
            "budgets": {"execution_time": 30},
            "max_concurrent": 2,
            "timeout_seconds": 25,
            "max_retries": 2,
            "max_iterations": 3,
            "formatting_rules": ["lowercase"]
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_config_missing_objective(self):
        """Test validation failure for missing objective"""
        config = {
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30}
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "objective" in error_msg

    def test_validate_config_missing_tools(self):
        """Test validation failure for missing tools"""
        config = {
            "objective": "Process text",
            "budgets": {"execution_time": 30}
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "tools" in error_msg

    def test_validate_config_empty_tools(self):
        """Test validation failure for empty tools list"""
        config = {
            "objective": "Process text",
            "tools": [],
            "budgets": {"execution_time": 30}
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "non-empty list" in error_msg

    def test_validate_config_invalid_tools(self):
        """Test validation failure for invalid tools"""
        config = {
            "objective": "Process text",
            "tools": ["invalid_tool", "another_invalid"],
            "budgets": {"execution_time": 30}
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "Invalid tool" in error_msg

    def test_validate_config_missing_budgets(self):
        """Test validation failure for missing budgets"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"]
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "budgets" in error_msg

    def test_validate_config_invalid_budgets_type(self):
        """Test validation failure for invalid budgets type"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": "invalid"
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "dictionary" in error_msg

    def test_validate_config_excessive_concurrency(self):
        """Test validation failure for excessive concurrency"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_concurrent": 15  # > 10 limit
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "max_concurrent" in error_msg

    def test_validate_config_excessive_timeout(self):
        """Test validation failure for excessive timeout"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "timeout_seconds": 45  # > 30 limit
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "timeout_seconds" in error_msg

    def test_validate_config_excessive_retries(self):
        """Test validation failure for excessive retries"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_retries": 5  # > 3 limit
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "max_retries" in error_msg

    def test_validate_config_boundary_values(self):
        """Test validation with boundary values"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_concurrent": 10,  # Exactly at limit
            "timeout_seconds": 30,  # Exactly at limit
            "max_retries": 3  # Exactly at limit
        }

        is_valid, error_msg = validate_config(config)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_config_exception_handling(self):
        """Test validation handles exceptions gracefully"""
        # Invalid config that might cause exception
        config = None

        is_valid, error_msg = validate_config(config)
        assert is_valid is False
        assert "validation error" in error_msg


class TestAgentBoundedExecution:
    """Unit tests for agent bounded execution"""

    @pytest.mark.asyncio
    async def test_execute_agent_bounded_objective_achieved(self):
        """Test agent execution that achieves objective"""
        config = {
            "objective": "Format text to lowercase",
            "tools": ["formatter"],
            "budgets": {"execution_time": 30},
            "max_iterations": 2,
            "formatting_rules": ["lowercase"]
        }

        with patch('server.services.agent_service.llm_service') as mock_llm, \
             patch('server.services.agent_service.formatter_service') as mock_formatter:

            # Mock LLM to return "complete" on first call
            mock_llm.call_llm = AsyncMock(return_value="complete")

            result = await execute_agent_bounded(config, "TEST INPUT")

            assert result["termination_reason"] == "objective_achieved"
            assert result["iterations"] == 1
            assert "execution_time" in result
            assert result["output_text"] == "TEST INPUT"

    @pytest.mark.asyncio
    async def test_execute_agent_bounded_max_iterations(self):
        """Test agent execution that hits max iterations"""
        config = {
            "objective": "Impossible task",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_iterations": 2
        }

        with patch('server.services.agent_service.llm_service') as mock_llm:
            # Mock LLM to never return "complete"
            mock_llm.call_llm = AsyncMock(return_value="continue")

            result = await execute_agent_bounded(config, "TEST INPUT")

            assert result["termination_reason"] == "max_iterations_reached"
            assert result["iterations"] == 2
            assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_execute_agent_bounded_timeout(self):
        """Test agent execution that times out"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "timeout_seconds": 0.1,  # Very short timeout
            "max_iterations": 10
        }

        with patch('server.services.agent_service.llm_service') as mock_llm:
            # Mock LLM with delay
            async def slow_llm_call(*args, **kwargs):
                await asyncio.sleep(0.2)  # Longer than timeout
                return "continue"

            mock_llm.call_llm = slow_llm_call

            result = await execute_agent_bounded(config, "TEST INPUT")

            assert result["termination_reason"] == "timeout_exceeded"
            assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_execute_agent_bounded_llm_timeout_retry(self):
        """Test agent execution with LLM timeout and retry logic"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "timeout_seconds": 10,
            "max_retries": 2,
            "max_iterations": 3
        }

        with patch('server.services.agent_service.llm_service') as mock_llm:
            # Mock LLM to timeout on first calls, succeed on later call
            call_count = 0

            async def mock_llm_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise asyncio.TimeoutError()
                return "complete"

            mock_llm.call_llm = mock_llm_call

            result = await execute_agent_bounded(config, "TEST INPUT")

            assert result["termination_reason"] == "objective_achieved"
            assert call_count == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_execute_agent_bounded_formatter_tool(self):
        """Test agent execution using formatter tool"""
        config = {
            "objective": "Format text",
            "tools": ["formatter"],
            "budgets": {"execution_time": 30},
            "max_iterations": 1,
            "formatting_rules": ["lowercase"]
        }

        with patch('server.services.agent_service.llm_service') as mock_llm, \
             patch('server.services.agent_service.formatter_service') as mock_formatter:

            # Mock LLM to choose formatter action
            mock_llm.call_llm = AsyncMock(return_value="formatter")
            mock_formatter.format_text = lambda text, config: text.lower()

            result = await execute_agent_bounded(config, "TEST INPUT")

            # Should have used formatter tool
            assert "execution_time" in result
            assert result["iterations"] >= 1

    @pytest.mark.asyncio
    async def test_execute_agent_bounded_error_handling(self):
        """Test agent execution error handling"""
        config = {
            "objective": "Process text",
            "tools": ["llm_call"],
            "budgets": {"execution_time": 30},
            "max_iterations": 1
        }

        with patch('server.services.agent_service.llm_service') as mock_llm:
            # Mock LLM to raise exception
            mock_llm.call_llm = AsyncMock(side_effect=Exception("LLM Error"))

            result = await execute_agent_bounded(config, "TEST INPUT")

            assert result["termination_reason"] == "error"
            assert "error_message" in result
            assert "LLM Error" in result["error_message"]