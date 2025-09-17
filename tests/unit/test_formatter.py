import pytest
from server.services.formatter_service import FormatterService


class TestFormatterService:
    """Unit tests for FormatterService - text transformation rules"""

    def setup_method(self):
        self.formatter = FormatterService()

    def test_lowercase_rule(self):
        """Test lowercase transformation rule"""
        result = self.formatter.apply_rule("Hello WORLD Test", "lowercase")
        assert result == "hello world test"

    def test_uppercase_rule(self):
        """Test uppercase transformation rule"""
        result = self.formatter.apply_rule("Hello World Test", "uppercase")
        assert result == "HELLO WORLD TEST"

    def test_full_to_half_rule(self):
        """Test full-width to half-width character transformation"""
        # Full-width ASCII characters to half-width
        full_width_text = "Ｈｅｌｌｏ　Ｗｏｒｌｄ！"
        result = self.formatter.apply_rule(full_width_text, "full_to_half")
        expected = "Hello World!"
        assert result == expected

    def test_half_to_full_rule(self):
        """Test half-width to full-width character transformation"""
        # Half-width ASCII characters to full-width
        half_width_text = "Hello World!"
        result = self.formatter.apply_rule(half_width_text, "half_to_full")
        expected = "Ｈｅｌｌｏ　Ｗｏｒｌｄ！"
        assert result == expected

    def test_rule_order_matters(self):
        """Test that rule application order affects final result"""
        text = "HELLO World"

        # Apply lowercase then uppercase
        result1 = self.formatter.apply_rules(text, ["lowercase", "uppercase"])
        assert result1 == "HELLO WORLD"

        # Apply uppercase then lowercase
        result2 = self.formatter.apply_rules(text, ["uppercase", "lowercase"])
        assert result2 == "hello world"

        # Results should be different
        assert result1 != result2

    def test_multiple_rules_application(self):
        """Test applying multiple rules in sequence"""
        text = "ＨＥＬＬＯ　Ｗｏｒｌｄ！"
        rules = ["full_to_half", "lowercase"]
        result = self.formatter.apply_rules(text, rules)
        expected = "hello world!"
        assert result == expected

    def test_empty_rules_list(self):
        """Test that empty rules list returns original text"""
        text = "Hello World"
        result = self.formatter.apply_rules(text, [])
        assert result == text

    def test_empty_text_with_rules(self):
        """Test applying rules to empty text"""
        result = self.formatter.apply_rules("", ["lowercase", "uppercase"])
        assert result == ""

    def test_whitespace_handling(self):
        """Test that whitespace is preserved correctly"""
        text = "  Hello   World  "
        result = self.formatter.apply_rule(text, "lowercase")
        assert result == "  hello   world  "

    def test_special_characters_preservation(self):
        """Test that special characters are preserved"""
        text = "Hello@#$%^&*()World!"
        result = self.formatter.apply_rule(text, "lowercase")
        assert result == "hello@#$%^&*()world!"

    def test_numbers_handling(self):
        """Test that numbers are handled correctly"""
        text = "Test123Number456"
        result = self.formatter.apply_rule(text, "lowercase")
        assert result == "test123number456"

    def test_unicode_characters(self):
        """Test handling of various Unicode characters"""
        text = "Café naïve résumé"
        result = self.formatter.apply_rule(text, "uppercase")
        assert result == "CAFÉ NAÏVE RÉSUMÉ"

    def test_mixed_case_complex(self):
        """Test complex mixed case scenarios"""
        text = "CamelCaseText_with-VARIOUS.formats"
        result = self.formatter.apply_rule(text, "lowercase")
        assert result == "camelcasetext_with-various.formats"

    def test_newlines_and_tabs(self):
        """Test handling of newlines and tabs"""
        text = "Line1\nLine2\tTabbed"
        result = self.formatter.apply_rule(text, "uppercase")
        assert result == "LINE1\nLINE2\tTABBED"

    def test_rule_validation(self):
        """Test validation of rule names"""
        with pytest.raises(ValueError, match="Unknown formatting rule"):
            self.formatter.apply_rule("test", "invalid_rule")

    def test_consecutive_same_rules(self):
        """Test applying the same rule multiple times"""
        text = "Hello World"
        result = self.formatter.apply_rules(text, ["lowercase", "lowercase", "lowercase"])
        assert result == "hello world"

    def test_reversible_rules(self):
        """Test that some rules are reversible"""
        original = "Hello World"

        # Apply lowercase then uppercase
        intermediate = self.formatter.apply_rule(original, "lowercase")
        result = self.formatter.apply_rule(intermediate, "uppercase")

        assert result == "HELLO WORLD"

    def test_full_half_width_roundtrip(self):
        """Test full-width to half-width and back"""
        original = "Hello World!"

        # Convert to full-width then back to half-width
        full_width = self.formatter.apply_rule(original, "half_to_full")
        back_to_half = self.formatter.apply_rule(full_width, "full_to_half")

        assert back_to_half == original

    def test_long_text_performance(self):
        """Test performance with longer text"""
        long_text = "Lorem ipsum dolor sit amet " * 100
        result = self.formatter.apply_rule(long_text, "lowercase")
        assert len(result) == len(long_text)
        assert result == long_text.lower()

    def test_validate_config_valid_rules(self):
        """Test config validation with valid rules"""
        valid_config = {"rules": ["lowercase", "uppercase"]}
        is_valid, error = self.formatter.validate_config(valid_config)
        assert is_valid is True
        assert error is None

    def test_validate_config_invalid_rules(self):
        """Test config validation with invalid rules"""
        invalid_config = {"rules": ["lowercase", "invalid_rule"]}
        is_valid, error = self.formatter.validate_config(invalid_config)
        assert is_valid is False
        assert "invalid_rule" in error

    def test_validate_config_missing_rules(self):
        """Test config validation with missing rules field"""
        invalid_config = {}
        is_valid, error = self.formatter.validate_config(invalid_config)
        assert is_valid is False
        assert "Missing required field" in error

    def test_validate_config_non_list_rules(self):
        """Test config validation with non-list rules"""
        invalid_config = {"rules": "lowercase"}
        is_valid, error = self.formatter.validate_config(invalid_config)
        assert is_valid is False
        assert "must be a list" in error