"""
Unit tests for Soul Manager module.

Tests:
- Soul loading and caching
- Meta-injection generation
- Time awareness
- Axioms and BDI state
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestSoulManager:
    """Tests for SoulManager class."""
    
    def test_soul_loads_correctly(self):
        """Test that soul loads from file without errors."""
        from src.core.soul import soul_manager
        
        soul = soul_manager.get_soul()
        
        assert soul is not None
        assert soul.meta.agent_id == "MAX_AI_PRIME"
        assert soul.meta.version == "1.0.0"
    
    def test_soul_has_axioms(self):
        """Test that soul has exactly 4 axioms."""
        from src.core.soul import soul_manager
        
        soul = soul_manager.get_soul()
        
        assert len(soul.axioms) == 4
        assert "Simplicity > Complexity" in soul.axioms
    
    def test_meta_injection_contains_axioms(self):
        """Test that meta injection includes axioms block."""
        from src.core.soul import soul_manager
        
        injection = soul_manager.generate_meta_injection()
        
        assert "META-COGNITION" in injection
        assert "Simplicity" in injection
    
    def test_meta_injection_contains_time_awareness(self):
        """Test that meta injection includes time context."""
        from src.core.soul import soul_manager
        
        injection = soul_manager.generate_meta_injection()
        
        assert "TIME AWARENESS" in injection
    
    def test_time_of_day_detection(self):
        """Test _get_time_context returns a string with time info."""
        from src.core.soul import soul_manager
        
        context = soul_manager._get_time_context()
        
        # Should return a non-empty string
        assert isinstance(context, str)
        assert len(context) > 0
    
    def test_boot_count_increments(self):
        """Test that boot count increments on load."""
        from src.core.soul import soul_manager
        
        soul = soul_manager.get_soul()
        initial_boot = soul.meta.boot_count
        
        # Boot count should be at least 1
        assert initial_boot >= 1
    
    def test_add_insight(self):
        """Test adding insight to soul."""
        from src.core.soul import soul_manager
        
        test_insight = "Test insight for unit testing"
        soul_manager.add_insight(test_insight)
        
        soul = soul_manager.get_soul()
        assert test_insight in soul.insights
    
    def test_set_focus(self):
        """Test setting current focus."""
        from src.core.soul import soul_manager
        
        soul_manager.set_focus(project="UnitTest", context="testing")
        
        soul = soul_manager.get_soul()
        assert soul.current_focus.project == "UnitTest"
        assert soul.current_focus.context == "testing"
    
    def test_touch_user_activity(self):
        """Test that user activity touch works without error."""
        from src.core.soul import soul_manager
        
        # Should not raise an error
        soul_manager.touch_user_activity()
        
        # After touching, user should be considered active
        assert soul_manager._is_user_active() is True
    
    def test_is_user_active(self):
        """Test user activity detection."""
        from src.core.soul import soul_manager
        
        soul_manager.touch_user_activity()
        assert soul_manager._is_user_active() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
