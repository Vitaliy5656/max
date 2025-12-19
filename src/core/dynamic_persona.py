"""
Dynamic Persona — User Style Rules Management.

Implements:
1. DynamicPersona - Manages explicit user rules for System Prompt injection
2. FeedbackLoopAnalyzer - Analyzes user reactions and extracts style rules via LLM

Together with adaptation.py, this creates a complete adaptive response system.
"""
import asyncio
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path

import aiosqlite

from .config import config
from .logger import log


@dataclass
class UserRule:
    """A user preference rule for response adaptation."""
    id: int
    rule_content: str
    source: str  # 'manual', 'feedback', 'llm_analysis'
    weight: float
    is_active: bool
    
    def __str__(self) -> str:
        return self.rule_content


class DynamicPersona:
    """
    Manages user-specific rules for System Prompt injection.
    
    Rules are stored in the user_preferences table and injected
    into every LLM request to adapt response style.
    
    Example rules:
    - "Отвечай короче"
    - "Не использовать эмодзи"
    - "Уровень сарказма: высокий"
    """
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
        self._base_persona_path = Path(__file__).parent.parent.parent / "data" / "system_prompt.txt"
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        log.api("🎭 DynamicPersona initialized")
    
    def _load_base_persona(self) -> str:
        """Load static base persona from file."""
        try:
            if self._base_persona_path.exists():
                return self._base_persona_path.read_text(encoding="utf-8")
        except Exception as e:
            log.error(f"Failed to load base persona: {e}")
        return "Ты MAX — интеллектуальный AI-ассистент."
    
    async def get_active_rules(self, user_id: str = "default") -> list[UserRule]:
        """Get all active rules for a user, ordered by weight."""
        if not self._db:
            return []
        
        async with self._db.execute("""
            SELECT id, rule_content, source, weight, is_active
            FROM user_preferences
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY weight DESC, created_at DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
        
        return [
            UserRule(
                id=row[0],
                rule_content=row[1],
                source=row[2],
                weight=row[3],
                is_active=bool(row[4])
            )
            for row in rows
        ]
    
    async def add_rule(
        self,
        rule_content: str,
        source: str = "manual",
        weight: float = 1.0,
        user_id: str = "default"
    ) -> int:
        """
        Add a new rule to user preferences.
        
        Args:
            rule_content: The rule text
            source: Where the rule came from ('manual', 'feedback', 'llm_analysis')
            weight: Priority of the rule (higher = more important)
            user_id: User identifier
            
        Returns:
            ID of the created rule
        """
        if not self._db:
            log.error("DynamicPersona: DB not initialized")
            return -1
        
        # Check for duplicate
        async with self._db.execute(
            "SELECT id FROM user_preferences WHERE rule_content = ? AND user_id = ?",
            (rule_content, user_id)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                log.debug(f"Rule already exists: {rule_content[:50]}...")
                return existing[0]
        
        cursor = await self._db.execute("""
            INSERT INTO user_preferences (user_id, rule_content, source, weight)
            VALUES (?, ?, ?, ?)
        """, (user_id, rule_content, source, weight))
        await self._db.commit()
        
        log.api(f"🎭 New rule added [{source}]: {rule_content}")
        return cursor.lastrowid
    
    async def deactivate_rule(self, rule_id: int) -> bool:
        """Deactivate a rule (soft delete)."""
        if not self._db:
            return False
        
        cursor = await self._db.execute(
            "UPDATE user_preferences SET is_active = FALSE WHERE id = ?",
            (rule_id,)
        )
        await self._db.commit()
        
        if cursor.rowcount > 0:
            log.api(f"🎭 Rule {rule_id} deactivated")
            return True
        return False
    
    async def delete_rule(self, rule_id: int) -> bool:
        """Permanently delete a rule."""
        if not self._db:
            return False
        
        cursor = await self._db.execute(
            "DELETE FROM user_preferences WHERE id = ?",
            (rule_id,)
        )
        await self._db.commit()
        
        return cursor.rowcount > 0
    
    async def build_dynamic_prompt(self, user_id: str = "default") -> str:
        """
        Build complete system prompt with user rules injected.
        
        Structure:
        1. Base persona (from system_prompt.txt)
        2. User rules section (if any)
        
        Returns:
            Complete system prompt string
        """
        # 1. Load base persona
        base_persona = self._load_base_persona()
        
        # 2. Get active rules
        rules = await self.get_active_rules(user_id)
        
        if not rules:
            return base_persona
        
        # 3. Format rules list
        rules_list = "\n".join([f"- {rule}" for rule in rules])
        
        # 4. Combine into final prompt
        full_prompt = f"""{base_persona}

### 🧠 ВАЖНО: ПЕРСОНАЛЬНЫЕ НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ
Адаптируй ответ под следующие правила:
{rules_list}
"""
        
        log.debug(f"🎭 Dynamic prompt built with {len(rules)} rules")
        return full_prompt


class FeedbackLoopAnalyzer:
    """
    Analyzes user reactions and extracts style rules via LLM.
    
    Triggers:
    - Explicit dissatisfaction phrases ("хватит болтать", "короче")
    - Negative feedback (dislike button)
    
    Process:
    1. Detect trigger in user message
    2. Call lightweight LLM to extract rule
    3. Save rule to user_preferences
    """
    
    DISSATISFACTION_TRIGGERS = [
        # Russian triggers
        "хватит болтать",
        "короче",
        "не надо воды",
        "давай быстрее",
        "без лирики",
        "к делу",
        "слишком длинно",
        "много текста",
        "не так многословно",
        "покороче",
        "лаконичнее",
        "без воды",
        "не растекайся",
        "суть",
        "кратко",
        # English triggers
        "too long",
        "be brief",
        "get to the point",
        "stop rambling",
        "too verbose",
        "shorter please",
        "tldr",
    ]
    
    def __init__(
        self,
        db: Optional[aiosqlite.Connection] = None,
        dynamic_persona: Optional[DynamicPersona] = None
    ):
        self._db = db
        self._persona = dynamic_persona or DynamicPersona()
    
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        await self._persona.initialize(db)
        log.api("🔄 FeedbackLoopAnalyzer initialized")
    
    def detect_dissatisfaction(self, user_msg: str) -> bool:
        """Check if user message contains dissatisfaction triggers."""
        user_lower = user_msg.lower()
        
        for trigger in self.DISSATISFACTION_TRIGGERS:
            if trigger in user_lower:
                log.debug(f"🔄 Dissatisfaction detected: '{trigger}'")
                return True
        
        return False
    
    async def analyze_feedback(
        self,
        last_user_msg: str,
        last_bot_msg: str,
        lm_client: Any = None
    ) -> Optional[str]:
        """
        Analyze user reaction and extract a rule if dissatisfaction detected.
        
        This method is called as a background task after each response.
        
        Args:
            last_user_msg: User's reaction/follow-up message
            last_bot_msg: Assistant's previous response
            lm_client: LM client for rule extraction
            
        Returns:
            Extracted rule text, or None if no rule extracted
        """
        # 1. Check for dissatisfaction
        if not self.detect_dissatisfaction(last_user_msg):
            return None
        
        log.api(f"🔄 Analyzing feedback: '{last_user_msg[:50]}...'")
        
        # 2. Try LLM-based extraction if client available
        if lm_client:
            rule = await self._extract_rule_via_llm(
                last_user_msg, last_bot_msg, lm_client
            )
        else:
            # Fallback: simple pattern-based extraction
            rule = self._extract_simple_rule(last_user_msg)
        
        if not rule:
            return None
        
        # 3. Save rule to database
        await self._persona.add_rule(
            rule_content=rule,
            source="feedback",
            weight=1.5  # Feedback-derived rules get higher priority
        )
        
        return rule
    
    def _extract_simple_rule(self, user_msg: str) -> str:
        """Extract a simple rule based on patterns (no LLM)."""
        user_lower = user_msg.lower()
        
        # Pattern → Rule mapping
        patterns = {
            "короче": "Отвечай короче и лаконичнее",
            "хватит болтать": "Избегай лишних рассуждений, давай прямой ответ",
            "без воды": "Минимум воды, максимум полезной информации",
            "слишком длинно": "Ограничь длину ответов до 2-3 абзацев",
            "без эмодзи": "Не использовать эмодзи в ответах",
            "без лирики": "Без лирических отступлений, строго по делу",
            "к делу": "Сразу к делу, без вступлений",
            "too long": "Keep responses concise",
            "be brief": "Respond briefly",
        }
        
        for pattern, rule in patterns.items():
            if pattern in user_lower:
                return rule
        
        # Default rule for unrecognized patterns
        return "Адаптируй стиль под предпочтения пользователя"
    
    async def _extract_rule_via_llm(
        self,
        user_msg: str,
        bot_msg: str,
        lm_client: Any
    ) -> Optional[str]:
        """
        Use lightweight LLM to extract specific rule from feedback.
        
        Uses extraction/small model for efficiency.
        """
        try:
            prompt = f"""Пользователь выразил недовольство ответом ассистента.

ОТВЕТ АССИСТЕНТА (сокращённо):
"{bot_msg[:500]}..."

РЕАКЦИЯ ПОЛЬЗОВАТЕЛЯ:
"{user_msg}"

ЗАДАЧА: Выдели, что именно не понравилось пользователю в стиле ответа.
Сформулируй это как ОДНО краткое правило для System Prompt (до 10 слов).

Примеры выходных правил:
- "Отвечать короче"
- "Не использовать эмодзи"
- "Давать только код без объяснений"
- "Не задавать уточняющих вопросов"

ПРАВИЛО:"""

            # Use extraction model (lightweight)
            response = await lm_client.client.chat.completions.create(
                model=config.memory.extraction_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.3
            )
            
            rule = response.choices[0].message.content.strip()
            
            # Clean up: remove quotes, bullet points
            rule = rule.strip('"\'- •').strip()
            
            if len(rule) > 3 and len(rule) < 100:
                log.api(f"🧠 LLM extracted rule: {rule}")
                return rule
            
        except Exception as e:
            log.error(f"LLM rule extraction failed: {e}")
        
        # Fallback to simple extraction
        return self._extract_simple_rule(user_msg)


# Global instances
dynamic_persona = DynamicPersona()
feedback_loop = FeedbackLoopAnalyzer()


async def initialize_dynamic_persona(db: aiosqlite.Connection):
    """Initialize all dynamic persona components with database."""
    await dynamic_persona.initialize(db)
    await feedback_loop.initialize(db)
