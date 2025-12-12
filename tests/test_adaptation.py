"""
Tests for Adaptation module.

ALIGNED WITH REAL API.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAdaptationImports:
    """Tests for adaptation module imports."""
    
    def test_imports_exist(self):
        """Test that all expected classes can be imported."""
        from src.core.adaptation import (
            CorrectionDetector,
            FeedbackMiner,
            FactEffectivenessTracker,
            AdaptivePromptBuilder,
            AnticipationEngine
        )
        
        assert CorrectionDetector is not None
        assert FeedbackMiner is not None
        assert FactEffectivenessTracker is not None
        assert AdaptivePromptBuilder is not None
        assert AnticipationEngine is not None


class TestCorrectionDetector:
    """Tests for CorrectionDetector class."""
    
    def test_detector_instantiation(self):
        """Test CorrectionDetector can be instantiated."""
        from src.core.adaptation import CorrectionDetector
        
        detector = CorrectionDetector()
        assert detector is not None
        
    def test_detect_method_exists(self):
        """Test detect method exists."""
        from src.core.adaptation import CorrectionDetector
        
        detector = CorrectionDetector()
        assert hasattr(detector, 'detect')
        
    def test_detect_returns_dict(self):
        """Test detect returns expected structure."""
        from src.core.adaptation import CorrectionDetector
        
        detector = CorrectionDetector()
        result = detector.detect("Test message")
        
        assert isinstance(result, dict)
        assert "is_correction" in result


class TestAnticipationEngine:
    """Tests for AnticipationEngine class."""
    
    def test_engine_instantiation(self):
        """Test AnticipationEngine can be instantiated."""
        from src.core.adaptation import AnticipationEngine
        
        engine = AnticipationEngine()
        assert engine is not None
        
    def test_has_get_suggestions(self):
        """Test get_suggestions method exists."""
        from src.core.adaptation import AnticipationEngine
        
        engine = AnticipationEngine()
        assert hasattr(engine, 'get_suggestions')


class TestAdaptivePromptBuilder:
    """Tests for AdaptivePromptBuilder class."""
    
    def test_builder_instantiation(self):
        """Test AdaptivePromptBuilder can be instantiated."""
        from src.core.adaptation import AdaptivePromptBuilder
        
        builder = AdaptivePromptBuilder()
        assert builder is not None
        
    def test_has_build_method(self):
        """Test build method exists."""
        from src.core.adaptation import AdaptivePromptBuilder
        
        builder = AdaptivePromptBuilder()
        assert hasattr(builder, 'build')


class TestGlobalInstances:
    """Tests for global adaptation instances."""
    
    def test_global_instances_exist(self):
        """Test global instances can be imported."""
        from src.core.adaptation import (
            correction_detector,
            feedback_miner,
            fact_tracker,
            prompt_builder,
            anticipation_engine
        )
        
        assert correction_detector is not None
        assert anticipation_engine is not None
        
    def test_initialize_adaptation_function(self):
        """Test initialize_adaptation function exists."""
        from src.core.adaptation import initialize_adaptation
        
        assert callable(initialize_adaptation)
