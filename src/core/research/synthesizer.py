"""
Synthesizer Agent for Deep Research.
Handles final aggregation of facts into a high-quality structured report.
"""
import json
from typing import List, Dict, Any
from ..lm_client import lm_client, TaskType

class ResearchSynthesizer:
    def __init__(self, model_type: TaskType = TaskType.REASONING):
        self.model_type = model_type

    async def generate_report(self, goal: str, facts: List[Dict[str, Any]], format: str = "markdown") -> str:
        """
        Synthesizes research facts into a structured report with source tracking.
        """
        # 1. Cluster facts if there are many
        if len(facts) > 15:
            clusters = await self.cluster_facts([f.get("content", "") for f in facts])
        else:
            clusters = {"General": [f.get("content", "") for f in facts]}

        # 2. Prepare facts with source URLs
        facts_text = ""
        sources = {}
        for i, f in enumerate(facts, 1):
            tag = f.get("tag", "н/д")
            content = f.get("content", "")
            url = f.get("url", "")
            
            ref_num = ""
            if url:
                if url not in sources:
                    sources[url] = len(sources) + 1
                ref_num = f" [^src{sources[url]}^]"
            
            facts_text += f"{i}. [{tag}] {content}{ref_num}\n"

        # 3. Add sources list to prompt context
        sources_text = "\n".join([f"[^src{idx}^]: {url}" for url, idx in sources.items()])

        prompt = f"""Ты - Главный Синтезатор Deep Research.
Твоя цель: Подготовить итоговый структурированный отчет по теме: "{goal}"

У тебя есть следующие собранные факты:
{facts_text}

Источники:
{sources_text}

ТРЕБОВАНИЯ К ОТЧЕТУ:
1. Используй профессиональный тон.
2. Структурируй по разделам (Введение, Ключевые находки, Детальный анализ, Заключение).
3. Указывай степень достоверности (используй теги верификации).
4. Если есть противоречия - выдели их.
5. ОБЯЗАТЕЛЬНО используй сноски [^srcX^] для подтверждения фактов там, где они были в исходных данных.
6. В конце отчета добавь раздел "Список источников".
7. Формат: {format}.

Ответь ТОЛЬКО готовым текстом отчета."""
        
        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=self.model_type,
                max_tokens=4000,
                stream=False
            )
            return response
        except Exception as e:
            return f"Ошибка синтеза отчета: {str(e)}"

    async def cluster_facts(self, facts: List[str]) -> Dict[str, List[str]]:
        """
        Groups facts into thematic clusters using LLM.
        """
        if not facts:
            return {"General": []}
            
        facts_joint = "\n---\n".join(facts[:30])
        prompt = f"""Сгруппируй следующие факты по 3-5 основным темам.
Факты:
{facts_joint}

Ответь в формате JSON: {{"Тема1": ["факт1", "факт2"], "Тема2": [...]}}"""
        
        try:
            response = await lm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                task_type=TaskType.QUICK,
                max_tokens=2000,
                stream=False
            )
            # Simple JSON parse
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0:
                return json.loads(response[start:end])
        except:
            pass
            
        return {"General": facts}
