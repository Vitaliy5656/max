"""
Prompt Library for MAX AI.

Hierarchical system for managing specialized prompts (personas).
Prompts are selected based on intent, topic, and keywords.

Structure:
    - Base prompts (system defaults)
    - Domain prompts (astronomy, coding, etc.)
    - User prompts (custom, editable)
"""
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

from ..logger import log


class PromptCategory(Enum):
    """Categories for organizing prompts."""
    SYSTEM = "system"      # Core system prompts
    DOMAIN = "domain"      # Domain expertise (astronomy, jewelry, etc.)
    PERSONA = "persona"    # Character/personality (therapist, coder, etc.)
    USER = "user"          # User-defined custom prompts
    TASK = "task"          # Task-specific (code review, translation, etc.)


@dataclass
class Prompt:
    """Single prompt definition."""
    id: str
    name: str
    system_prompt: str
    category: PromptCategory = PromptCategory.DOMAIN
    
    # Matching criteria
    intents: List[str] = field(default_factory=list)  # ["coding", "question"]
    topics: List[str] = field(default_factory=list)   # ["astronomy", "physics"]
    keywords: List[str] = field(default_factory=list) # ["star", "planet"]
    
    # UI
    icon: str = "💬"
    description: str = ""
    
    # Settings
    temperature: Optional[float] = None  # Override default
    is_active: bool = True
    priority: int = 0  # Higher = preferred when multiple match


# Built-in prompts
BUILTIN_PROMPTS: List[Prompt] = [
    # System
    Prompt(
        id="default",
        name="MAX Assistant",
        icon="🤖",
        category=PromptCategory.SYSTEM,
        system_prompt="",  # Empty — identity comes from Soul Manager's Iron Mask
        intents=["greeting", "chitchat", "question", "*"],  # Preferred for casual
        priority=100  # HIGH priority for default identity
    ),
    
    # Personas
    Prompt(
        id="coder",
        name="Code Master",
        icon="💻",
        category=PromptCategory.PERSONA,
        system_prompt="""Ты опытный программист-архитектор. 
Пишешь чистый, эффективный код. 
Объясняешь решения и предлагаешь лучшие практики.
Всегда указываешь на потенциальные баги и улучшения.""",
        intents=["coding"],
        keywords=["код", "функция", "баг", "python", "javascript"],
        temperature=0.3,
        priority=10
    ),
    
    Prompt(
        id="therapist",
        name="Поддержка",
        icon="💚",
        category=PromptCategory.PERSONA,
        system_prompt="""Ты эмпатичный слушатель и психологическая поддержка.
Никогда не осуждаешь, всегда поддерживаешь.
Используешь техники активного слушания.
Помогаешь разобраться в эмоциях и найти решения.""",
        intents=["psychology"],
        keywords=["грустно", "плохо", "тревога", "депрессия", "устал"],
        temperature=0.7,
        priority=10
    ),
    
    Prompt(
        id="researcher",
        name="Исследователь",
        icon="🔬",
        category=PromptCategory.PERSONA,
        system_prompt="""Ты исследователь с научным подходом.
Ищешь достоверную информацию и цитируешь источники.
Разделяешь факты и гипотезы.
Объясняешь сложное простыми словами.""",
        intents=["search", "question"],
        temperature=0.5,
        priority=5
    ),
    
    Prompt(
        id="creative_writer",
        name="Писатель",
        icon="✍️",
        category=PromptCategory.PERSONA,
        system_prompt="""Ты талантливый писатель с богатой фантазией.
Создаёшь захватывающие истории, яркие образы.
Владеешь разными стилями: от поэзии до прозы.
Пишешь с душой и вдохновением.""",
        intents=["creative"],
        keywords=["напиши", "история", "стих", "рассказ"],
        temperature=0.9,
        priority=10
    ),
    
    # Domain experts
    # NOTE: Domain prompts ONLY activate when topic or keywords match!
    # They have priority=15, but select() now requires topic/keyword match for DOMAIN category.
    Prompt(
        id="astronomy_expert",
        name="Астроном",
        icon="🔭",
        category=PromptCategory.DOMAIN,
        system_prompt="""Ты профессиональный астроном и популяризатор науки.
Знаешь всё о звёздах, планетах, галактиках и космосе.
Объясняешь сложные концепции простым языком.
Делишься актуальными новостями космонавтики.""",
        topics=["astronomy", "space", "physics"],
        keywords=["звезда", "планета", "галактика", "космос", "телескоп", 
                  "чёрная дыра", "спутник", "орбита", "NASA", "SpaceX"],
        priority=15  # Only applies if topic/keyword matches
    ),
    
    Prompt(
        id="jewelry_expert",
        name="Ювелир",
        icon="💎",
        category=PromptCategory.DOMAIN,
        system_prompt="""Ты эксперт-геммолог с 20-летним опытом.
Разбираешься в драгоценных камнях, металлах, огранке.
Помогаешь выбирать украшения и оценивать качество.
Знаешь историю ювелирного искусства.""",
        topics=["jewelry", "gems"],
        keywords=["бриллиант", "карат", "золото", "серебро", "огранка",
                  "кольцо", "ожерелье", "рубин", "изумруд", "сапфир"],
        priority=15
    ),
    
    Prompt(
        id="constructor",
        name="Строитель",
        icon="🏗️",
        category=PromptCategory.DOMAIN,
        system_prompt="""Ты опытный инженер-строитель.
Разбираешься в материалах, технологиях, нормативах.
Помогаешь с расчётами и планированием работ.
Даёшь практичные советы по ремонту и строительству.""",
        topics=["construction", "building"],
        keywords=["фундамент", "стена", "кровля", "бетон", "кирпич",
                  "ремонт", "стройка", "материал", "смета"],
        priority=15
    ),
    
    # Tasks
    Prompt(
        id="translator",
        name="Переводчик",
        icon="🌐",
        category=PromptCategory.TASK,
        system_prompt="""Ты профессиональный переводчик.
Переводишь точно, сохраняя смысл и стиль.
Объясняешь нюансы перевода если нужно.
Владеешь русским и английским на высшем уровне.""",
        intents=["translation"],
        temperature=0.3,
        priority=10
    ),
    
    Prompt(
        id="math_solver",
        name="Математик",
        icon="📐",
        category=PromptCategory.TASK,
        system_prompt="""Ты математик-преподаватель.
Решаешь задачи пошагово, объясняя каждый шаг.
Проверяешь ответы и указываешь на ошибки.
Используешь визуальные примеры когда это помогает.""",
        intents=["math"],
        temperature=0.2,
        priority=10
    ),
]


class PromptLibrary:
    """
    Manages prompts with hierarchical selection.
    
    Selection priority:
        1. Exact topic match (highest)
        2. Intent + keywords match
        3. Intent only match
        4. Default fallback
    """
    
    def __init__(self):
        self._prompts: Dict[str, Prompt] = {}
        self._load_builtin()
        
        log.debug(f"PromptLibrary initialized with {len(self._prompts)} prompts")
    
    def _load_builtin(self) -> None:
        """Load built-in prompts."""
        for prompt in BUILTIN_PROMPTS:
            self._prompts[prompt.id] = prompt
    
    def get(self, prompt_id: str) -> Optional[Prompt]:
        """Get prompt by ID."""
        return self._prompts.get(prompt_id)
    
    def select(
        self,
        intent: Optional[str] = None,
        topic: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        message: Optional[str] = None
    ) -> Prompt:
        """
        Select best matching prompt.
        
        Args:
            intent: Detected intent (coding, question, etc.)
            topic: Detected topic (astronomy, jewelry, etc.)
            keywords: Extracted keywords
            message: Original message for keyword matching
            
        Returns:
            Best matching prompt (or default)
        """
        candidates: List[tuple[int, Prompt]] = []
        
        message_lower = message.lower() if message else ""
        keywords = keywords or []
        
        for prompt in self._prompts.values():
            if not prompt.is_active:
                continue
            
            score = 0
            has_domain_match = False  # Track if domain prompt has relevant match
            
            # Topic match (highest priority)
            if topic and topic in prompt.topics:
                score += 100
                has_domain_match = True
            
            # Keyword match (important for domain activation)
            if prompt.keywords:
                matched_kw = sum(1 for kw in prompt.keywords if kw in message_lower)
                if matched_kw > 0:
                    score += matched_kw * 10
                    has_domain_match = True
            
            # 🛡️ DOMAIN FILTER: Domain prompts ONLY activate with topic/keyword match
            # This prevents "Астроном" from hijacking "Привет" greetings
            if prompt.category == PromptCategory.DOMAIN and not has_domain_match:
                continue  # Skip domain prompts without relevant context
            
            # Intent match
            if intent:
                if intent in prompt.intents:
                    score += 50
                elif "*" in prompt.intents:
                    score += 1  # Fallback match
            
            # Add priority
            score += prompt.priority
            
            if score > 0:
                candidates.append((score, prompt))
        
        if not candidates:
            return self._prompts["default"]
        
        # Sort by score (descending)
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        winner = candidates[0][1]
        log.debug(f"PromptLibrary selected: {winner.name} (score={candidates[0][0]})")
        
        return winner
    
    def list_all(self) -> List[Prompt]:
        """List all prompts."""
        return list(self._prompts.values())
    
    def list_by_category(self, category: PromptCategory) -> List[Prompt]:
        """List prompts in category."""
        return [p for p in self._prompts.values() if p.category == category]
    
    def add(self, prompt: Prompt) -> None:
        """Add or update prompt."""
        self._prompts[prompt.id] = prompt
        log.debug(f"Added prompt: {prompt.id}")
    
    def remove(self, prompt_id: str) -> bool:
        """Remove prompt by ID."""
        if prompt_id in self._prompts and prompt_id != "default":
            del self._prompts[prompt_id]
            return True
        return False
    
    def get_for_display(self) -> List[Dict[str, Any]]:
        """Get prompts formatted for UI display."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "icon": p.icon,
                "category": p.category.value,
                "description": p.description or p.system_prompt[:100],
            }
            for p in self._prompts.values()
            if p.is_active
        ]


# Global instance
_library: Optional[PromptLibrary] = None


def get_prompt_library() -> PromptLibrary:
    """Get or create global PromptLibrary."""
    global _library
    if _library is None:
        _library = PromptLibrary()
    return _library


def select_prompt(
    intent: Optional[str] = None,
    topic: Optional[str] = None,
    message: Optional[str] = None
) -> Prompt:
    """Quick prompt selection."""
    return get_prompt_library().select(intent=intent, topic=topic, message=message)
