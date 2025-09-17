import os
import asyncio
import httpx
from typing import Dict, Any, Optional, List, Tuple
from fastapi import HTTPException
import logging
import json

logger = logging.getLogger(__name__)

class LLMService:
    """Service for handling LLM API calls"""

    def __init__(self):
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.api_key = os.getenv("LLM_API_KEY")
        self.timeout = 60  # 60 seconds timeout
        self.supported_models = [
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-5"
        ]

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate LLM node configuration
        Returns: (is_valid, error_message)
        """
        try:
            # Check required fields
            if "model" not in config:
                return False, "Missing required field: 'model'"

            if "prompt" not in config:
                return False, "Missing required field: 'prompt'"

            # Validate model
            model = config["model"]
            if model not in self.supported_models:
                return False, f"Unsupported model: {model}. Supported models: {', '.join(self.supported_models)}"

            # Validate prompt contains placeholder
            prompt = config["prompt"]
            logger.info(f"LLM validation - received prompt: '{prompt}'")
            logger.info(f"LLM validation - prompt contains {{text}}: {'{text}' in prompt}")
            if "{text}" not in prompt:
                return False, "Prompt must contain '{text}' placeholder for input text"

            # Validate optional parameters
            if "temperature" in config:
                temp = config["temperature"]
                if not isinstance(temp, (int, float)) or temp < 0.0 or temp > 2.0:
                    return False, "Temperature must be a number between 0.0 and 2.0"

            if "max_tokens" in config:
                max_tokens = config["max_tokens"]
                if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 4096:
                    return False, "max_tokens must be an integer between 1 and 4096"

            if "top_p" in config:
                top_p = config["top_p"]
                if not isinstance(top_p, (int, float)) or top_p < 0.0 or top_p > 1.0:
                    return False, "top_p must be a number between 0.0 and 1.0"

            return True, None

        except Exception as e:
            logger.error(f"Error validating LLM config: {str(e)}")
            return False, f"Error validating configuration: {str(e)}"

    async def call_llm(self, input_text: str, config: Dict[str, Any]) -> str:
        """
        Make async call to LLM API
        Returns: LLM response text
        """
        try:
            # Validate configuration first
            is_valid, error_msg = self.validate_config(config)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid LLM config: {error_msg}")

            # Check API key
            if not self.api_key:
                raise HTTPException(
                    status_code=500,
                    detail="LLM API key not configured. Please set LLM_API_KEY environment variable."
                )

            # Prepare prompt with input text
            prompt = config["prompt"].format(text=input_text)

            # Prepare API request
            request_data = {
                "model": config["model"],
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": config.get("temperature", 0.7),
                "max_tokens": config.get("max_tokens", 150),
            }

            # Add optional parameters
            if "top_p" in config:
                request_data["top_p"] = config["top_p"]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Log request (sanitized)
            logger.info(
                "Making LLM API call",
                extra={
                    "model": config["model"],
                    "prompt_length": len(prompt),
                    "input_text_length": len(input_text),
                    "api_base": self.api_base
                }
            )

            # Make API call
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=request_data
                )

                # Handle API errors
                if response.status_code == 401:
                    raise HTTPException(
                        status_code=500,
                        detail="LLM API authentication failed. Please check LLM_API_KEY."
                    )
                elif response.status_code == 429:
                    raise HTTPException(
                        status_code=429,
                        detail="LLM API rate limit exceeded. Please try again later."
                    )
                elif response.status_code >= 400:
                    error_detail = "LLM API request failed"
                    try:
                        error_data = response.json()
                        if "error" in error_data and "message" in error_data["error"]:
                            error_detail = error_data["error"]["message"]
                    except:
                        pass
                    raise HTTPException(
                        status_code=500,
                        detail=f"LLM API error: {error_detail}"
                    )

                # Parse response
                response_data = response.json()

                if "choices" not in response_data or len(response_data["choices"]) == 0:
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid response from LLM API: no choices returned"
                    )

                result_text = response_data["choices"][0]["message"]["content"]

                # Log response (sanitized)
                logger.info(
                    "LLM API call completed",
                    extra={
                        "response_length": len(result_text),
                        "usage": response_data.get("usage", {}),
                        "model": config["model"]
                    }
                )

                return result_text

        except HTTPException:
            raise
        except asyncio.TimeoutError:
            logger.error("LLM API call timed out")
            raise HTTPException(
                status_code=504,
                detail=f"LLM API call timed out after {self.timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"LLM service error: {str(e)}"
            )

    def sanitize_logs(self, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize sensitive data from logs
        Returns: sanitized log data
        """
        sanitized = {
            "model": request_data.get("model"),
            "prompt_length": len(request_data.get("messages", [{}])[0].get("content", "")),
            "temperature": request_data.get("temperature"),
            "max_tokens": request_data.get("max_tokens"),
            "response_length": len(response_data.get("choices", [{}])[0].get("message", {}).get("content", "")),
            "usage": response_data.get("usage", {})
        }
        return sanitized


# Global service instance
llm_service = LLMService()