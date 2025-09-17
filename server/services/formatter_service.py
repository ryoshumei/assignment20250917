from typing import Dict, List, Any, Optional, Tuple
from fastapi import HTTPException
import logging
import re

logger = logging.getLogger(__name__)

class FormatterService:
    """Service for text formatting operations"""

    def __init__(self):
        self.supported_rules = [
            "lowercase",
            "uppercase",
            "half_to_full",
            "full_to_half"
        ]

    def validate_rules(self, rules: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate formatter rules configuration
        Returns: (is_valid, error_message)
        """
        try:
            if not isinstance(rules, list):
                return False, "Rules must be a list"

            # Empty rules list is valid (pass-through)
            if len(rules) == 0:
                return True, None

            # Check all rules are supported
            for rule in rules:
                if rule not in self.supported_rules:
                    return False, f"Unsupported rule: '{rule}'. Supported rules: {', '.join(self.supported_rules)}"

            return True, None

        except Exception as e:
            logger.error(f"Error validating formatter rules: {str(e)}")
            return False, f"Error validating rules: {str(e)}"

    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate formatter node configuration
        Returns: (is_valid, error_message)
        """
        try:
            if "rules" not in config:
                return False, "Missing required field: 'rules'"

            rules = config["rules"]
            return self.validate_rules(rules)

        except Exception as e:
            logger.error(f"Error validating formatter config: {str(e)}")
            return False, f"Error validating configuration: {str(e)}"

    def apply_rule(self, text: str, rule: str) -> str:
        """
        Apply a single formatting rule to text
        Returns: formatted text
        """
        return self.apply_rules(text, [rule])

    def apply_rules(self, text: str, rules: List[str]) -> str:
        """
        Apply formatting rules to text in order
        Returns: formatted text
        """
        try:
            # Validate rules first
            is_valid, error_msg = self.validate_rules(rules)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid formatter rules: {error_msg}")

            result = text

            # Apply rules in order
            for rule in rules:
                if rule == "lowercase":
                    result = self._apply_lowercase(result)
                elif rule == "uppercase":
                    result = self._apply_uppercase(result)
                elif rule == "half_to_full":
                    result = self._apply_half_to_full(result)
                elif rule == "full_to_half":
                    result = self._apply_full_to_half(result)

                logger.debug(f"Applied rule '{rule}': {len(result)} characters")

            logger.info(f"Applied {len(rules)} formatting rules to text")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error applying formatter rules: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Formatter service error: {str(e)}")

    def _apply_lowercase(self, text: str) -> str:
        """Convert text to lowercase"""
        return text.lower()

    def _apply_uppercase(self, text: str) -> str:
        """Convert text to uppercase"""
        return text.upper()

    def _apply_half_to_full(self, text: str) -> str:
        """Convert half-width characters to full-width"""
        # ASCII to full-width mapping
        result = ""
        for char in text:
            code = ord(char)
            # Convert ASCII space (0x20) to full-width space (0x3000)
            if code == 0x20:
                result += chr(0x3000)
            # Convert ASCII printable characters (0x21-0x7E) to full-width (0xFF01-0xFF5E)
            elif 0x21 <= code <= 0x7E:
                result += chr(code - 0x21 + 0xFF01)
            else:
                result += char
        return result

    def _apply_full_to_half(self, text: str) -> str:
        """Convert full-width characters to half-width"""
        # Full-width to ASCII mapping
        result = ""
        for char in text:
            code = ord(char)
            # Convert full-width space (0x3000) to ASCII space (0x20)
            if code == 0x3000:
                result += chr(0x20)
            # Convert full-width printable characters (0xFF01-0xFF5E) to ASCII (0x21-0x7E)
            elif 0xFF01 <= code <= 0xFF5E:
                result += chr(code - 0xFF01 + 0x21)
            else:
                result += char
        return result

    def format_text(self, text: str, config: Dict[str, Any]) -> str:
        """
        Format text using configuration
        Returns: formatted text
        """
        try:
            # Validate configuration
            is_valid, error_msg = self.validate_config(config)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid formatter config: {error_msg}")

            rules = config["rules"]

            # If no rules specified, return original text
            if len(rules) == 0:
                logger.info("No formatting rules specified, returning original text")
                return text

            # Apply rules
            return self.apply_rules(text, rules)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error formatting text: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Text formatting error: {str(e)}")


# Global service instance
formatter_service = FormatterService()