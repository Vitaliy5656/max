"""
Unit tests for Model Loader module.

Tests:
- LMS CLI availability check
- Model configuration
- Load/unload functions
"""
import pytest
from unittest.mock import patch, MagicMock


class TestModelLoader:
    """Tests for Model Loader functions."""
    
    def test_is_lms_available(self):
        """Test LMS availability check."""
        from src.core.model_loader import is_lms_available
        
        # Should return True if lms is in PATH
        result = is_lms_available()
        assert isinstance(result, bool)
    
    def test_model_configs_exist(self):
        """Test that MODEL_CONFIGS is defined."""
        from src.core.model_loader import MODEL_CONFIGS
        
        assert MODEL_CONFIGS is not None
        assert len(MODEL_CONFIGS) >= 3
    
    def test_model_configs_format(self):
        """Test that MODEL_CONFIGS has correct format."""
        from src.core.model_loader import MODEL_CONFIGS
        
        for config in MODEL_CONFIGS:
            assert len(config) == 3
            model_pattern, gpu_setting, identifier = config
            assert isinstance(model_pattern, str)
            assert gpu_setting in ['max', 'off', '0', '1'] or isinstance(gpu_setting, float)
            assert isinstance(identifier, str)
    
    def test_qwen_on_gpu_max(self):
        """Test that Qwen is configured for max GPU."""
        from src.core.model_loader import MODEL_CONFIGS
        
        qwen_config = next((c for c in MODEL_CONFIGS if 'qwen' in c[0].lower()), None)
        assert qwen_config is not None
        assert qwen_config[1] == 'max'
    
    def test_phi_on_cpu(self):
        """Test that Phi-3 is configured for CPU only."""
        from src.core.model_loader import MODEL_CONFIGS
        
        phi_config = next((c for c in MODEL_CONFIGS if 'phi' in c[0].lower()), None)
        assert phi_config is not None
        assert phi_config[1] == 'off'
    
    def test_embeddings_on_cpu(self):
        """Test that embeddings are configured for CPU."""
        from src.core.model_loader import MODEL_CONFIGS
        
        embed_config = next((c for c in MODEL_CONFIGS if 'embed' in c[0].lower()), None)
        assert embed_config is not None
        assert embed_config[1] == 'off'
    
    @patch('subprocess.run')
    def test_load_model_calls_subprocess(self, mock_run):
        """Test that load_model calls subprocess with correct args."""
        from src.core.model_loader import load_model, is_lms_available
        
        if not is_lms_available():
            pytest.skip("LMS CLI not available")
        
        mock_run.return_value = MagicMock(returncode=0)
        
        load_model("test-model", gpu="max")
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "lms" in call_args
        assert "load" in call_args
        assert "--gpu" in call_args
        assert "max" in call_args
    
    def test_get_loaded_models_returns_list(self):
        """Test that get_loaded_models returns a list."""
        from src.core.model_loader import get_loaded_models
        
        result = get_loaded_models()
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
