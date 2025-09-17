from typing import Dict, Any, List, Tuple
import time
import asyncio
from ..services.llm_service import llm_service
from ..services.pdf_service import pdf_service
from ..services.formatter_service import formatter_service


class AgentConfigError(Exception):
    """Raised when agent configuration is invalid"""
    pass


def validate_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate agent configuration according to policy limits.

    Args:
        config: Agent configuration dictionary

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        # Required fields
        if "objective" not in config:
            return False, "Agent config missing required field: objective"

        if "tools" not in config:
            return False, "Agent config missing required field: tools"

        # Tools whitelist validation
        tools = config["tools"]
        if not isinstance(tools, list) or len(tools) == 0:
            return False, "Agent tools must be a non-empty list"

        valid_tools = {"pdf_extract", "formatter", "llm_call"}
        for tool in tools:
            if tool not in valid_tools:
                return False, f"Invalid tool '{tool}'. Valid tools: {valid_tools}"

        # Budgets validation when tools are used
        if "budgets" not in config:
            return False, "Agent config missing required field: budgets"

        budgets = config["budgets"]
        if not isinstance(budgets, dict):
            return False, "Agent budgets must be a dictionary"

        # Concurrency limits
        max_concurrent = config.get("max_concurrent", 1)
        if not isinstance(max_concurrent, int) or max_concurrent < 1 or max_concurrent > 10:
            return False, "max_concurrent must be an integer between 1 and 10"

        # Timeout limits
        timeout_seconds = config.get("timeout_seconds", 30)
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0 or timeout_seconds > 30:
            return False, "timeout_seconds must be a number between 0 and 30"

        # Retry limits
        max_retries = config.get("max_retries", 3)
        if not isinstance(max_retries, int) or max_retries < 0 or max_retries > 3:
            return False, "max_retries must be an integer between 0 and 3"

        return True, ""

    except Exception as e:
        return False, f"Agent config validation error: {str(e)}"


async def execute_agent_bounded(config: Dict[str, Any], input_text: str) -> Dict[str, Any]:
    """
    Execute agent with bounded loop and strict policy enforcement.

    Args:
        config: Validated agent configuration
        input_text: Input text to process

    Returns:
        Dict containing: output_text, termination_reason, iterations, execution_time
    """
    start_time = time.time()
    max_iterations = config.get("max_iterations", 5)
    objective = config["objective"]
    tools = config["tools"]
    budgets = config["budgets"]
    max_concurrent = config.get("max_concurrent", 1)
    timeout_seconds = config.get("timeout_seconds", 30)
    max_retries = config.get("max_retries", 3)

    current_text = input_text
    iterations = 0
    execution_log = []

    try:
        for iteration in range(max_iterations):
            iterations += 1
            iteration_start = time.time()

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                return {
                    "output_text": current_text,
                    "termination_reason": "timeout_exceeded",
                    "iterations": iterations,
                    "execution_time": elapsed,
                    "execution_log": execution_log
                }

            # Determine next action based on objective and available tools
            action_prompt = f"""
            Objective: {objective}
            Available tools: {tools}
            Current state: {current_text[:500]}...

            Determine the next action to achieve the objective. Choose from: {tools} or 'complete' if objective achieved.
            Respond with just the tool name or 'complete'.
            """

            # Call LLM to determine next action (with retry logic)
            action = None
            for retry in range(max_retries + 1):
                try:
                    action_response = await asyncio.wait_for(
                        llm_service.call_llm(action_prompt, {"model": "gpt-4o-mini", "prompt": "{text}"}),
                        timeout=min(timeout_seconds - elapsed, 10)
                    )
                    action = action_response.strip().lower()
                    break
                except asyncio.TimeoutError:
                    if retry == max_retries:
                        return {
                            "output_text": current_text,
                            "termination_reason": "llm_timeout",
                            "iterations": iterations,
                            "execution_time": time.time() - start_time,
                            "execution_log": execution_log
                        }
                    await asyncio.sleep(2 ** retry)  # Exponential backoff

            execution_log.append({
                "iteration": iteration + 1,
                "action": action,
                "timestamp": time.time() - start_time
            })

            # Check completion
            if action == "complete":
                return {
                    "output_text": current_text,
                    "termination_reason": "objective_achieved",
                    "iterations": iterations,
                    "execution_time": time.time() - start_time,
                    "execution_log": execution_log
                }

            # Execute tool action
            if action == "llm_call" and "llm_call" in tools:
                # Use LLM to process current text towards objective
                llm_prompt = f"Objective: {objective}\n\nProcess this text: {current_text}"
                try:
                    current_text = await asyncio.wait_for(
                        llm_service.call_llm(llm_prompt, {"model": "gpt-4o-mini", "prompt": "{text}"}),
                        timeout=min(timeout_seconds - elapsed, 10)
                    )
                except asyncio.TimeoutError:
                    execution_log.append({"error": "llm_timeout"})
                    continue

            elif action == "formatter" and "formatter" in tools:
                # Apply formatting rules
                formatting_rules = config.get("formatting_rules", ["lowercase"])
                current_text = formatter_service.format_text(current_text, {"rules": formatting_rules})

            elif action == "pdf_extract" and "pdf_extract" in tools:
                # This would typically extract from a file_id in the text
                # For now, we'll skip if no file reference found
                if "file_id:" not in current_text:
                    execution_log.append({"warning": "pdf_extract requested but no file_id found"})
                    continue

        # Max iterations reached
        return {
            "output_text": current_text,
            "termination_reason": "max_iterations_reached",
            "iterations": iterations,
            "execution_time": time.time() - start_time,
            "execution_log": execution_log
        }

    except Exception as e:
        return {
            "output_text": current_text,
            "termination_reason": "error",
            "error_message": str(e),
            "iterations": iterations,
            "execution_time": time.time() - start_time,
            "execution_log": execution_log
        }