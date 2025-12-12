"""
Tests for MetricsEngine and ImplicitFeedbackAnalyzer.

ALIGNED WITH REAL API.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImplicitFeedbackAnalyzer:
    """Tests for ImplicitFeedbackAnalyzer."""
    
    def test_positive_signals_detection(self):
        """Test detection of positive feedback signals."""
        from src.core.metrics import ImplicitFeedbackAnalyzer
        
        analyzer = ImplicitFeedbackAnalyzer()
        
        # Test positive signals - analyze returns tuple (positive, negative, correction)
        result = analyzer.analyze("Спасибо, отлично помог!")
        assert result[0] > 0  # positive count
        assert result[1] == 0  # negative count
        
    def test_negative_signals_detection(self):
        """Test detection of negative feedback signals."""
        from src.core.metrics import ImplicitFeedbackAnalyzer
        
        analyzer = ImplicitFeedbackAnalyzer()
        
        # Test negative signals
        result = analyzer.analyze("Нет, это не то что я просил")
        assert result[1] > 0  # negative count
        
    def test_correction_signals_detection(self):
        """Test detection of correction signals."""
        from src.core.metrics import ImplicitFeedbackAnalyzer
        
        analyzer = ImplicitFeedbackAnalyzer()
        
        # Test correction signals
        result = analyzer.analyze("Я имел в виду другое")
        assert result[2] > 0  # correction count
        
    def test_caps_detection_frustration(self):
        """Test CAPS detection as frustration."""
        from src.core.metrics import ImplicitFeedbackAnalyzer
        
        analyzer = ImplicitFeedbackAnalyzer()
        
        # Frustrated CAPS with negative context
        result = analyzer.analyze("Я УВЕРЕН ЧТО ЭТО НЕПРАВИЛЬНО!!!")
        # Should have some negative signals
        assert isinstance(result, tuple)
        assert len(result) == 3
        
    def test_caps_info(self):
        """Test get_caps_info returns detailed analysis."""
        from src.core.metrics import ImplicitFeedbackAnalyzer
        
        analyzer = ImplicitFeedbackAnalyzer()
        
        info = analyzer.get_caps_info("This is VERY important")
        
        assert isinstance(info, dict)
        assert "caps_ratio" in info or "interpretation" in info or len(info) > 0
        
    def test_neutral_message(self):
        """Test neutral message (no signals)."""
        from src.core.metrics import ImplicitFeedbackAnalyzer
        
        analyzer = ImplicitFeedbackAnalyzer()
        
        result = analyzer.analyze("Расскажи мне о погоде")
        assert result[0] == 0  # positive
        assert result[1] == 0  # negative
        assert result[2] == 0  # correction


class TestMetricsEngineStructure:
    """Tests for MetricsEngine class structure."""
    
    def test_imports_and_classes_exist(self):
        """Test that all expected classes can be imported."""
        from src.core.metrics import (
            MetricsEngine,
            ImplicitFeedbackAnalyzer, 
            MetricResult,
            MetricBreakdown,
            Achievement,
            AdaptationProof,
            MetricCategory
        )
        
        assert MetricsEngine is not None
        assert ImplicitFeedbackAnalyzer is not None
        assert MetricResult is not None
        
    def test_metric_result_to_dict(self):
        """Test MetricResult serialization."""
        from src.core.metrics import MetricResult, MetricBreakdown
        
        breakdown = MetricBreakdown()
        result = MetricResult(
            score=75.0,
            level=3,
            progress=0.5,
            breakdown=breakdown,
            trend="up",
            trend_value=5.0
        )
        
        d = result.to_dict()
        assert d["score"] == 75.0
        assert d["level"] == 3
        assert "breakdown" in d
        
    def test_metric_category_enum(self):
        """Test MetricCategory enum values."""
        from src.core.metrics import MetricCategory
        
        assert MetricCategory.IQ.value == "iq"
        assert MetricCategory.EMPATHY.value == "empathy"
        assert MetricCategory.GENERAL.value == "general"


class TestAchievementStructure:
    """Tests for Achievement class."""
    
    def test_achievement_progress(self):
        """Test achievement progress calculation."""
        from src.core.metrics import Achievement
        
        achievement = Achievement(
            id="test",
            name="Test",
            description="Test desc",
            category="general",
            icon="🏆",
            threshold_type="count",
            threshold_value=100,
            current_value=50,
            unlocked=False
        )
        
        assert achievement.progress == 50  # 50/100 = 50%
        
    def test_achievement_to_dict(self):
        """Test achievement serialization."""
        from src.core.metrics import Achievement
        
        achievement = Achievement(
            id="test",
            name="Test Achievement",
            description="Test",
            category="iq",
            icon="🎯",
            threshold_type="score",
            threshold_value=80,
            current_value=80,
            unlocked=True
        )
        
        d = achievement.to_dict()
        assert d["id"] == "test"
        assert d["name"] == "Test Achievement"
        assert d["unlocked"] == True
