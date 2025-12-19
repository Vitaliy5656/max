"""
Tests for Dynamic Persona module.

Tests:
- DynamicPersona: add_rule, get_active_rules, build_dynamic_prompt
- FeedbackLoopAnalyzer: detect_dissatisfaction, analyze_feedback
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDynamicPersonaImports:
    """Tests for dynamic_persona module imports."""
    
    def test_imports_exist(self):
        """Test that all expected classes can be imported."""
        from src.core.dynamic_persona import (
            DynamicPersona,
            FeedbackLoopAnalyzer,
            UserRule,
            dynamic_persona,
            feedback_loop,
            initialize_dynamic_persona
        )
        
        assert DynamicPersona is not None
        assert FeedbackLoopAnalyzer is not None
        assert UserRule is not None
        assert dynamic_persona is not None
        assert feedback_loop is not None
        assert callable(initialize_dynamic_persona)


class TestDynamicPersona:
    """Tests for DynamicPersona class."""
    
    def test_instantiation(self):
        """Test DynamicPersona can be instantiated."""
        from src.core.dynamic_persona import DynamicPersona
        
        persona = DynamicPersona()
        assert persona is not None
    
    def test_has_required_methods(self):
        """Test required methods exist."""
        from src.core.dynamic_persona import DynamicPersona
        
        persona = DynamicPersona()
        assert hasattr(persona, 'get_active_rules')
        assert hasattr(persona, 'add_rule')
        assert hasattr(persona, 'deactivate_rule')
        assert hasattr(persona, 'delete_rule')
        assert hasattr(persona, 'build_dynamic_prompt')
        assert hasattr(persona, 'initialize')
    
    def test_load_base_persona(self):
        """Test base persona loading from file."""
        from src.core.dynamic_persona import DynamicPersona
        
        persona = DynamicPersona()
        base = persona._load_base_persona()
        
        # Should return non-empty string
        assert isinstance(base, str)
        assert len(base) > 10
        # Should contain MAX identity
        assert "MAX" in base or "max" in base.lower()


class TestFeedbackLoopAnalyzer:
    """Tests for FeedbackLoopAnalyzer class."""
    
    def test_instantiation(self):
        """Test FeedbackLoopAnalyzer can be instantiated."""
        from src.core.dynamic_persona import FeedbackLoopAnalyzer
        
        analyzer = FeedbackLoopAnalyzer()
        assert analyzer is not None
    
    def test_has_required_methods(self):
        """Test required methods exist."""
        from src.core.dynamic_persona import FeedbackLoopAnalyzer
        
        analyzer = FeedbackLoopAnalyzer()
        assert hasattr(analyzer, 'detect_dissatisfaction')
        assert hasattr(analyzer, 'analyze_feedback')
        assert hasattr(analyzer, 'initialize')
    
    def test_detect_dissatisfaction_positive(self):
        """Test dissatisfaction detection catches common phrases."""
        from src.core.dynamic_persona import FeedbackLoopAnalyzer
        
        analyzer = FeedbackLoopAnalyzer()
        
        # These should trigger dissatisfaction
        assert analyzer.detect_dissatisfaction("хватит болтать") == True
        assert analyzer.detect_dissatisfaction("Короче давай") == True
        assert analyzer.detect_dissatisfaction("слишком длинно") == True
        assert analyzer.detect_dissatisfaction("too long, be brief") == True
        assert analyzer.detect_dissatisfaction("без воды пожалуйста") == True
    
    def test_detect_dissatisfaction_negative(self):
        """Test dissatisfaction detection ignores normal messages."""
        from src.core.dynamic_persona import FeedbackLoopAnalyzer
        
        analyzer = FeedbackLoopAnalyzer()
        
        # These should NOT trigger dissatisfaction
        assert analyzer.detect_dissatisfaction("Привет, как дела?") == False
        assert analyzer.detect_dissatisfaction("Напиши функцию") == False
        assert analyzer.detect_dissatisfaction("Спасибо за помощь!") == False
        assert analyzer.detect_dissatisfaction("Объясни это") == False
    
    def test_extract_simple_rule(self):
        """Test simple rule extraction without LLM."""
        from src.core.dynamic_persona import FeedbackLoopAnalyzer
        
        analyzer = FeedbackLoopAnalyzer()
        
        # Test pattern matching
        rule = analyzer._extract_simple_rule("короче пиши")
        assert "короче" in rule.lower() or "лаконич" in rule.lower()
        
        rule = analyzer._extract_simple_rule("хватит болтать!")
        assert "прямой" in rule.lower() or "рассужден" in rule.lower()


class TestUserRule:
    """Tests for UserRule dataclass."""
    
    def test_dataclass_fields(self):
        """Test UserRule has expected fields."""
        from src.core.dynamic_persona import UserRule
        
        rule = UserRule(
            id=1,
            rule_content="Отвечай короче",
            source="manual",
            weight=1.5,
            is_active=True
        )
        
        assert rule.id == 1
        assert rule.rule_content == "Отвечай короче"
        assert rule.source == "manual"
        assert rule.weight == 1.5
        assert rule.is_active == True
    
    def test_str_representation(self):
        """Test UserRule string representation returns rule_content."""
        from src.core.dynamic_persona import UserRule
        
        rule = UserRule(
            id=1,
            rule_content="Не использовать эмодзи",
            source="feedback",
            weight=1.0,
            is_active=True
        )
        
        assert str(rule) == "Не использовать эмодзи"


class TestPreferencesRouter:
    """Tests for preferences API router."""
    
    def test_router_import(self):
        """Test router can be imported."""
        from src.api.routers.preferences import router
        
        assert router is not None
    
    def test_pydantic_models(self):
        """Test Pydantic models exist."""
        from src.api.routers.preferences import RuleCreate, RuleResponse
        
        # Test RuleCreate
        create = RuleCreate(rule="Test rule", weight=1.0)
        assert create.rule == "Test rule"
        assert create.weight == 1.0
        
        # Test RuleResponse
        response = RuleResponse(
            id=1,
            rule_content="Test",
            source="manual",
            weight=1.0,
            is_active=True
        )
        assert response.id == 1
