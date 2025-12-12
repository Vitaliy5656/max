"""
Configuration settings for MAX AI Assistant.
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class ThinkingModeConfig:
    """Configuration for a thinking mode."""
    model: str
    temperature: float
    max_tokens: int
    system_prompt_suffix: str = ""


@dataclass
class LMStudioConfig:
    """LM Studio server configuration."""
    base_url: str = "http://localhost:1234/v1"
    default_model: str = "deepseek-r1-distill-llama-8b"  # Default reasoning model
    vision_model: str = "mistral-community-pixtral-12b"  # For image analysis
    reasoning_model: str = "ministral-3-14b-reasoning"  # For deep thinking
    quick_model: str = "deepseek-r1-distill-llama-8b"  # For fast responses
    
    # Generation parameters
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    
    # Thinking time (seconds) - minimum wait for reasoning
    min_thinking_time: int = 0
    
    # Auto-unload TTL (seconds) - 0 = never unload
    auto_unload_ttl: int = 300  # 5 minutes

    # P2 Fix: Rate limiting (Concurrency)
    max_concurrent_requests: int = 5
    
    # Thinking Modes Configuration
    thinking_modes: dict = field(default_factory=lambda: {
        "fast": ThinkingModeConfig(
            model="deepseek-r1-distill-llama-8b",
            temperature=0.5,
            max_tokens=1024,
            system_prompt_suffix="Отвечай кратко и по делу. Без лишних рассуждений."
        ),
        "standard": ThinkingModeConfig(
            model="deepseek-r1-distill-llama-8b",
            temperature=0.7,
            max_tokens=4096,
            system_prompt_suffix=""
        ),
        "deep": ThinkingModeConfig(
            model="ministral-3-14b-reasoning",
            temperature=0.3,
            max_tokens=8192,
            system_prompt_suffix="""Думай шаг за шагом:
1. Проанализируй задачу
2. Рассмотри разные подходы  
3. Выбери лучший вариант
4. Дай развёрнутый ответ с объяснениями"""
        ),
        "vision": ThinkingModeConfig(
            model="mistral-community-pixtral-12b",
            temperature=0.5,
            max_tokens=4096,
            system_prompt_suffix="Внимательно рассмотри изображение и опиши что видишь."
        ),
    })


@dataclass
class MemoryConfig:
    """Memory system configuration."""
    # Session memory
    max_session_messages: int = 50
    max_context_tokens: int = 8000

    # Summarization threshold
    summarize_after_messages: int = 30
    # P3 Fix: Magic number extraction
    summary_token_ratio: float = 0.2

    # Facts extraction
    extract_facts: bool = True

    # Cross-session search
    cross_session_top_k: int = 5


@dataclass
class RAGConfig:
    """RAG engine configuration (P2 fix: extract hardcoded values)."""
    chunk_size: int = 500  # tokens per chunk
    chunk_overlap: int = 50  # overlap between chunks
    default_top_k: int = 5  # default number of results


@dataclass
class UserProfileConfig:
    """User personalization configuration."""
    enable_mood_detection: bool = True
    enable_style_adaptation: bool = True
    enable_feedback_learning: bool = True
    enable_soft_anticipation: bool = True
    
    # Mood detection sensitivity (0.0 - 1.0)
    mood_sensitivity: float = 0.5
    
    # Default style preferences
    default_verbosity: str = "balanced"  # "brief", "balanced", "detailed"
    default_formality: str = "friendly"  # "formal", "friendly", "casual"


@dataclass
class AppConfig:
    """Main application configuration."""
    # Paths - now using system-appropriate locations
    data_dir: Path = field(default_factory=lambda: _get_data_dir())
    db_path: Path = field(default_factory=lambda: _get_db_path())
    backup_dir: Path = field(default_factory=lambda: _get_backup_dir())
    
    # Server
    host: str = "127.0.0.1"
    port: int = 7860
    share: bool = False  # Gradio share link
    
    # Theme
    dark_mode: bool = True
    
    # Language
    default_language: str = "auto"  # "auto", "ru", "en"
    
    # Sub-configs
    lm_studio: LMStudioConfig = field(default_factory=LMStudioConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    user_profile: UserProfileConfig = field(default_factory=UserProfileConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    
    def __post_init__(self):
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)


# Lazy imports to avoid circular dependency
def _get_data_dir() -> Path:
    from .paths import get_app_data_dir
    return get_app_data_dir()

def _get_db_path() -> Path:
    from .paths import get_db_path
    return get_db_path()

def _get_backup_dir() -> Path:
    from .paths import get_backup_dir
    return get_backup_dir()


# Global config instance
config = AppConfig()
