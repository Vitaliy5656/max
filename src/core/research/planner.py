"""
Planner Agent for Deep Research.
Handles goal decomposition, multi-perspective query generation, and 'Editable CoT'.
"""
import json
from typing import List, Dict, Any, Optional
from ..lm_client import lm_client, TaskType

class ResearchPlanner:
    def __init__(self, model_type: TaskType = TaskType.REASONING):
        self.model_type = model_type

    async def create_initial_plan(self, goal: str) -> List[Dict[str, Any]]:
        """
        Create a detailed research plan with Perspective-Guided Planning (STORM).
        Instead of a linear list, generate 3 'Search Personas' to cover more ground.
        """
        prompt = f"""Ты - Главный Планировщик Deep Research.
Цель исследования: "{goal}"

Твоя задача: Составь план исследования, используя метод STORM (Perspective-Guided Planning).

1. Определи 3 ключевых ПЕРСОНЫ (роли), которые смотрят на эту проблему с разных сторон.
   Например: "Технический Эксперт", "Инвестор", "Конечный пользователь".
2. Для каждой персоны напиши 2 конкретных исследовательских вопроса.

Ответи в формате JSON:
{{
  "personas": [
    {{"name": "Роль 1", "queries": ["вопрос 1", "вопрос 2"]}},
    ...
  ],
  "general_aspects": ["аспект 1", "аспект 2"]
}}"""
        
        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=self.model_type,
                max_tokens=2000,
                stream=False
            )
            
            # Extract JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0:
                data = json.loads(response[json_start:json_end])
                
                plan = []
                # Add general aspects first
                for aspect in data.get("general_aspects", []):
                    plan.append({
                        "stage": "Обзор",
                        "description": aspect,
                        "queries": [aspect]
                    })
                
                # Add persona tasks
                for persona in data.get("personas", []):
                    plan.append({
                        "stage": persona["name"],
                        "description": f"Исследование с позиции {persona['name']}",
                        "queries": persona["queries"]
                    })
                return plan
                
        except Exception as e:
            print(f"Planner error: {e}")
            # Fallback plan
            return [
                {"stage": "Обзор", "description": f"Общее исследование {goal}", "queries": [goal]},
                {"stage": "Детали", "description": "Сбор фактов и деталей", "queries": [f"{goal} подробности"]},
                {"stage": "Синтез", "description": "Подготовка отчета", "queries": []}
            ]

    async def generate_sub_queries(self, goal: str, context: str) -> List[str]:
        """
        Generates additional queries based on current research progress (recursive research).
        """
        prompt = f"""На основе текущих находок:
{context[:2000]}

Цель исследования: {goal}

Какие еще 3 специализированных запроса нужно сделать, чтобы углубить исследование?
Ответь списком JSON: ["запрос 1", "запрос 2", "запрос 3"]"""

        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.QUICK,
                max_tokens=500
            )
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0:
                return json.loads(response[json_start:json_end])
        except:
            return []
        
        return []
