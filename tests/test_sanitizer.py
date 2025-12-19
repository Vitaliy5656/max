"""
Unit tests for TextSanitizer module.

Tests:
- Asterisk removal
- User: artifact removal
- Newline collapsing
- Chinese character removal
- Special token removal
- Stream cleaner
"""
import pytest


class TestTextSanitizer:
    """Tests for TextSanitizer class."""
    
    def test_removes_multiple_asterisks(self):
        """Test that *** gets reduced to **."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Hello***World")
        assert result == "Hello**World"
        
        result = sanitizer.clean_output("Test****Test")
        assert result == "Test**Test"
    
    def test_preserves_double_asterisks(self):
        """Test that ** (markdown bold) is preserved."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("**bold text**")
        assert result == "**bold text**"
    
    def test_removes_user_artifact(self):
        """Test that trailing User: is removed."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Hello User:")
        assert result == "Hello"
        
        result = sanitizer.clean_output("Response text User:   ")
        assert result == "Response text"
    
    def test_removes_assistant_artifact(self):
        """Test that trailing Assistant: is removed."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Some text Assistant:")
        assert result == "Some text"
    
    def test_collapses_newlines(self):
        """Test that multiple newlines collapse to 2."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Line1\n\n\n\nLine2")
        assert result == "Line1\n\nLine2"
    
    def test_preserves_double_newlines(self):
        """Test that exactly 2 newlines are preserved."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Line1\n\nLine2")
        assert result == "Line1\n\nLine2"
    
    def test_removes_chinese_at_end(self):
        """Test that Chinese characters at end are removed."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Hello中文")
        assert result == "Hello"
    
    def test_removes_im_end_token(self):
        """Test that im_end token and following text is removed."""
        from src.core.utils import sanitizer
        
        result = sanitizer.clean_output("Response text<|im_end|>garbage")
        assert result == "Response text"
    
    def test_stream_cleaner_removes_tokens(self):
        """Test that stream_cleaner removes special tokens."""
        from src.core.utils import sanitizer
        
        result = sanitizer.stream_cleaner("<|im_end|>")
        assert result == ""
        
        result = sanitizer.stream_cleaner("</s>")
        assert result == ""
    
    def test_stream_cleaner_preserves_normal_text(self):
        """Test that stream_cleaner keeps normal text."""
        from src.core.utils import sanitizer
        
        result = sanitizer.stream_cleaner("Hello World")
        assert result == "Hello World"
    
    def test_remove_trailing_artifacts(self):
        """Test remove_trailing_artifacts method."""
        from src.core.utils import sanitizer
        
        result = sanitizer.remove_trailing_artifacts("Text User:")
        assert result == "Text"
    
    def test_empty_input(self):
        """Test that empty input returns empty."""
        from src.core.utils import sanitizer
        
        assert sanitizer.clean_output("") == ""
        assert sanitizer.clean_output(None) is None
        assert sanitizer.stream_cleaner("") == ""


class TestSanitizerConfig:
    """Tests for SanitizerConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        from src.core.utils.sanitizer import SanitizerConfig
        
        config = SanitizerConfig()
        
        assert config.remove_asterisks is True
        assert config.remove_role_artifacts is True
        assert config.collapse_newlines is True
        assert config.max_newlines == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
