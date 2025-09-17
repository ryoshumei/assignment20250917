import pytest
from server.services.llm_service import LLMService


class TestLLMParameterValidation:
    """Unit tests for LLM service parameter validation"""

    def setup_method(self):
        self.llm_service = LLMService()

    def test_valid_minimal_config(self):
        """Test minimal valid configuration"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Summarize this text: {text}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is True
        assert error is None

    def test_valid_full_config(self):
        """Test complete valid configuration with all optional parameters"""
        config = {
            "model": "gpt-4o",
            "prompt": "Analyze the following content: {text}",
            "temperature": 0.5,
            "max_tokens": 150,
            "top_p": 0.9
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is True
        assert error is None

    def test_missing_model_field(self):
        """Test validation fails when model field is missing"""
        config = {
            "prompt": "Test prompt: {text}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "Missing required field: 'model'" in error

    def test_missing_prompt_field(self):
        """Test validation fails when prompt field is missing"""
        config = {
            "model": "gpt-4.1-mini"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "Missing required field: 'prompt'" in error

    def test_unsupported_model(self):
        """Test validation fails for unsupported model"""
        config = {
            "model": "unsupported-model",
            "prompt": "Test prompt: {text}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "Unsupported model" in error
        assert "unsupported-model" in error

    def test_prompt_missing_placeholder(self):
        """Test validation fails when prompt doesn't contain {text} placeholder"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "This prompt has no placeholder"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "{text}" in error
        assert "placeholder" in error

    def test_temperature_validation_boundaries(self):
        """Test temperature parameter boundary validation"""
        # Valid temperatures
        for temp in [0.0, 0.5, 1.0, 1.5, 2.0]:
            config = {
                "model": "gpt-4.1-mini",
                "prompt": "Test: {text}",
                "temperature": temp
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is True, f"Temperature {temp} should be valid"

        # Invalid temperatures
        for temp in [-0.1, 2.1, -1.0, 3.0]:
            config = {
                "model": "gpt-4.1-mini",
                "prompt": "Test: {text}",
                "temperature": temp
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is False, f"Temperature {temp} should be invalid"
            assert "Temperature must be a number between 0.0 and 2.0" in error

    def test_temperature_type_validation(self):
        """Test temperature parameter type validation"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Test: {text}",
            "temperature": "invalid"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "Temperature must be a number" in error

    def test_max_tokens_validation_boundaries(self):
        """Test max_tokens parameter boundary validation"""
        # Valid max_tokens
        for tokens in [1, 100, 1000, 4096]:
            config = {
                "model": "gpt-4.1-mini",
                "prompt": "Test: {text}",
                "max_tokens": tokens
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is True, f"max_tokens {tokens} should be valid"

        # Invalid max_tokens
        for tokens in [0, -1, 4097, 10000]:
            config = {
                "model": "gpt-4.1-mini",
                "prompt": "Test: {text}",
                "max_tokens": tokens
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is False, f"max_tokens {tokens} should be invalid"
            assert "max_tokens must be an integer between 1 and 4096" in error

    def test_max_tokens_type_validation(self):
        """Test max_tokens parameter type validation"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Test: {text}",
            "max_tokens": 150.5  # Float should be invalid
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "max_tokens must be an integer" in error

    def test_top_p_validation_boundaries(self):
        """Test top_p parameter boundary validation"""
        # Valid top_p values
        for top_p in [0.0, 0.1, 0.5, 0.9, 1.0]:
            config = {
                "model": "gpt-4.1-mini",
                "prompt": "Test: {text}",
                "top_p": top_p
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is True, f"top_p {top_p} should be valid"

        # Invalid top_p values
        for top_p in [-0.1, 1.1, -1.0, 2.0]:
            config = {
                "model": "gpt-4.1-mini",
                "prompt": "Test: {text}",
                "top_p": top_p
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is False, f"top_p {top_p} should be invalid"
            assert "top_p must be a number between 0.0 and 1.0" in error

    def test_top_p_type_validation(self):
        """Test top_p parameter type validation"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Test: {text}",
            "top_p": "invalid"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "top_p must be a number" in error

    def test_supported_models_list(self):
        """Test all supported models are accepted"""
        supported_models = ["gpt-4.1-mini", "gpt-4o", "gpt-5"]

        for model in supported_models:
            config = {
                "model": model,
                "prompt": "Test: {text}"
            }
            is_valid, error = self.llm_service.validate_config(config)
            assert is_valid is True, f"Model {model} should be supported"

    def test_prompt_with_multiple_placeholders(self):
        """Test prompt can contain {text} multiple times"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "First: {text}, then analyze: {text}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is True

    def test_prompt_with_other_placeholders(self):
        """Test prompt can contain other placeholders besides {text}"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Context: {context}, analyze: {text}, format: {format}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is True

    def test_extra_fields_ignored(self):
        """Test that extra fields in config are ignored gracefully"""
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Test: {text}",
            "extra_field": "should be ignored",
            "another_field": 123
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is True

    def test_empty_config(self):
        """Test validation fails for empty config"""
        config = {}
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "Missing required field" in error

    def test_none_values(self):
        """Test validation handles None values appropriately"""
        config = {
            "model": None,
            "prompt": "Test: {text}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "model" in error.lower()

    def test_validation_error_handling(self):
        """Test that validation handles unexpected errors gracefully"""
        # This test ensures the try-catch in validate_config works
        config = {
            "model": "gpt-4.1-mini",
            "prompt": "Test: {text}",
            "temperature": float('inf')  # This might cause an unexpected error
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert error is not None

    def test_case_sensitive_model_names(self):
        """Test that model names are case-sensitive"""
        config = {
            "model": "GPT-4.1-MINI",  # Wrong case
            "prompt": "Test: {text}"
        }
        is_valid, error = self.llm_service.validate_config(config)
        assert is_valid is False
        assert "Unsupported model" in error