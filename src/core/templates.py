"""
Prompt Templates Manager.

Features:
- Save and load prompt templates
- Categorization
- Usage tracking
"""
import uuid
from typing import Optional
from dataclasses import dataclass

import aiosqlite


@dataclass
class Template:
    """Saved prompt template."""
    id: str
    name: str
    description: Optional[str]
    prompt: str
    category: Optional[str]
    use_count: int = 0
    created_at: Optional[str] = None


class TemplateManager:
    """Manages prompt templates."""
    
    def __init__(self, db: Optional[aiosqlite.Connection] = None):
        self._db = db
        
    async def initialize(self, db: aiosqlite.Connection):
        """Initialize with database connection."""
        self._db = db
        
        # Add default templates if empty
        async with self._db.execute("SELECT COUNT(*) FROM templates") as cursor:
            row = await cursor.fetchone()
            if row[0] == 0:
                await self._add_default_templates()
    
    async def _add_default_templates(self):
        """Add default useful templates."""
        defaults = [
            Template(
                id=str(uuid.uuid4()),
                name="Объясни код",
                description="Объяснение кода с комментариями",
                prompt="Объясни этот код подробно, добавь комментарии:\n\n```\n{code}\n```",
                category="Код"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Рефакторинг",
                description="Улучшение структуры кода",
                prompt="Сделай рефакторинг этого кода, улучши читаемость и эффективность:\n\n```\n{code}\n```",
                category="Код"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Краткое резюме",
                description="Суммировать длинный текст",
                prompt="Кратко суммируй основные пункты этого текста (3-5 предложений):\n\n{text}",
                category="Текст"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Перевод RU→EN",
                description="Перевод с русского на английский",
                prompt="Переведи на английский:\n\n{text}",
                category="Перевод"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Перевод EN→RU",
                description="Перевод с английского на русский",
                prompt="Переведи на русский:\n\n{text}",
                category="Перевод"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Исправь ошибки",
                description="Грамматические и стилистические ошибки",
                prompt="Исправь грамматические и стилистические ошибки в тексте:\n\n{text}",
                category="Текст"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Bash команда",
                description="Генерация shell команды",
                prompt="Напиши bash команду для: {task}",
                category="Системы"
            ),
            Template(
                id=str(uuid.uuid4()),
                name="Анализ файла",
                description="Анализ содержимого файла",
                prompt="Проанализируй этот файл и расскажи что в нём:\n\nФайл: {filename}\n\nСодержимое:\n{content}",
                category="Файлы"
            ),
        ]
        
        for t in defaults:
            await self._db.execute(
                """INSERT INTO templates (id, name, description, prompt, category)
                   VALUES (?, ?, ?, ?, ?)""",
                (t.id, t.name, t.description, t.prompt, t.category)
            )
        await self._db.commit()
    
    async def add(
        self,
        name: str,
        prompt: str,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> Template:
        """Add a new template."""
        template = Template(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            prompt=prompt,
            category=category
        )
        
        await self._db.execute(
            """INSERT INTO templates (id, name, description, prompt, category)
               VALUES (?, ?, ?, ?, ?)""",
            (template.id, template.name, template.description, 
             template.prompt, template.category)
        )
        await self._db.commit()
        return template
    
    async def get(self, template_id: str) -> Optional[Template]:
        """Get template by ID."""
        async with self._db.execute(
            "SELECT * FROM templates WHERE id = ?", (template_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        return Template(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            prompt=row["prompt"],
            category=row["category"],
            use_count=row["use_count"],
            created_at=row["created_at"]
        )
    
    async def list_all(self, category: Optional[str] = None) -> list[Template]:
        """List all templates, optionally filtered by category."""
        if category:
            query = "SELECT * FROM templates WHERE category = ? ORDER BY use_count DESC"
            params = (category,)
        else:
            query = "SELECT * FROM templates ORDER BY use_count DESC"
            params = ()
        
        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        
        return [
            Template(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                prompt=row["prompt"],
                category=row["category"],
                use_count=row["use_count"],
                created_at=row["created_at"]
            )
            for row in rows
        ]
    
    async def get_categories(self) -> list[str]:
        """Get list of unique categories."""
        async with self._db.execute(
            "SELECT DISTINCT category FROM templates WHERE category IS NOT NULL"
        ) as cursor:
            rows = await cursor.fetchall()
        return [row[0] for row in rows]
    
    async def use(self, template_id: str, variables: dict) -> str:
        """
        Use a template by substituting variables.
        
        Args:
            template_id: Template ID
            variables: Dict of {placeholder: value}
            
        Returns:
            Filled template string
        """
        template = await self.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Increment use count
        await self._db.execute(
            "UPDATE templates SET use_count = use_count + 1 WHERE id = ?",
            (template_id,)
        )
        await self._db.commit()
        
        # Substitute variables
        result = template.prompt
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        # P3 Fix: Check for unreplaced placeholders
        import re
        unreplaced = re.findall(r'\{(\w+)\}', result)
        if unreplaced:
            # Log warning but don't fail - user might want literal braces
            print(f"[templates] Warning: Unreplaced placeholders: {unreplaced}")
        
        return result
    
    async def delete(self, template_id: str) -> bool:
        """Delete a template."""
        cursor = await self._db.execute(
            "DELETE FROM templates WHERE id = ?",
            (template_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0
    
    async def update(
        self,
        template_id: str,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """Update a template."""
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        if prompt:
            updates.append("prompt = ?")
            params.append(prompt)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        
        if not updates:
            return False
        
        params.append(template_id)
        
        cursor = await self._db.execute(
            f"UPDATE templates SET {', '.join(updates)} WHERE id = ?",
            params
        )
        await self._db.commit()
        return cursor.rowcount > 0


# Global template manager
templates = TemplateManager()
