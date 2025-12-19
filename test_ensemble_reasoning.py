"""
Ensemble Cognitive Loop v2 — HARDCORE STRESS TEST
===================================================
Targeted testing of reasoning capabilities with strict constraints.

Model: mistralai-mistral-nemo-instruct-2407-12b-mpoa-v1-i1 (via config)
"""
import asyncio
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Custom Hardcore Questions
TEST_QUESTIONS = [
    {
        "id": 1,
        "category": "math_hell",
        "description": "Математический ад: Поезда и JSON",
        "question": """Реши задачу, но строго соблюдай формат вывода.

Задача: Поезд А выехал из города X в город Y со скоростью 80 км/ч. Через 2 часа из города Y навстречу выехал поезд Б со скоростью 100 км/ч. Расстояние между городами 500 км. Через сколько времени после старта поезда Б они встретятся?

ТРЕБОВАНИЯ К ОТВЕТУ (ЖЕСТКО):

Ты должен думать вслух, но финальный ответ обязан быть упакован в JSON-формат.

В рассуждениях запрещено использовать слово "часов" или "ч", используй только "minutes" (минуты) для всех промежуточных расчетов.

Финальный JSON должен выглядеть так:

```json
{
  "train_A_speed": int,
  "train_B_speed": int,
  "distance_before_B_starts": int,
  "remaining_distance": int,
  "closing_speed": int,
  "meeting_time_minutes": float
}
```
Любое отклонение от JSON или использование слова "час" в рассуждениях — провал.""",
        "min_score": 7.0
    },
    {
        "id": 2,
        "category": "noir_detective",
        "description": "Нуарный детектив: Негативные ограничения",
        "question": """Ты — циничный детектив из нуарных фильмов 40-х годов. Ты стоишь под дождем и куришь.

Ситуация: На месте преступления найдены: разбитая ваза, мокрые следы от обуви, ведущие к окну, и свежий букет цветов на столе.

Задание: Выдвини 3 (три) версии произошедшего.

ЖЕСТКИЕ ОГРАНИЧЕНИЯ:

ЗАПРЕЩЕННЫЕ СЛОВА: Тебе категорически нельзя использовать слова: "вор", "преступник", "украл", "разбил", "убежал", "следы". Замени их на сленг или метафоры.

Формат: Каждая версия должна быть ровно в одно предложение. Не больше, не меньше.

Стиль: Используй мрачные метафоры, сравнивай всё с дождём, грязью или джазом.

Начни ответ с фразы: "Этот город прогнил насквозь..." """,
        "min_score": 7.0
    }
]


async def main():
    print("=" * 70)
    print("ENSEMBLE COGNITIVE LOOP v2 — HARDCORE MODE")
    print("=" * 70)
    
    # Import ensemble system
    from src.core.cognitive.ensemble_loop import ensemble_thinking
    from src.core.cognitive.ensemble_types import (
        EnsembleConfig, EnsembleState, get_config_for_mode
    )
    from src.core.config import config
    
    # Use standard config but slightly tweaked for strictness if needed
    cfg = get_config_for_mode("standard")
    cfg.timeout_total = 180.0 # Give it time to think
    
    print(f"[CONFIG] Model: {config.lm_studio.default_model}")
    print(f"         Mode: standard")
    print(f"         Temps: {cfg.temperatures}")
    
    results = {"passed": 0, "failed": 0}
    
    for tc in TEST_QUESTIONS:
        print("\n" + "=" * 70)
        print(f"[TEST {tc['id']}] {tc['description']}")
        print("=" * 70)
        
        start_time = time.time()
        final_result = None
        step_count = 0
        
        try:
            # Run ensemble thinking
            async for event in ensemble_thinking(
                question=tc["question"],
                context="Ты опытный эксперт, способный следовать сложным инструкциям.",
                config=cfg,
                question_type=tc["category"]
            ):
                if "thinking" in event:
                    step_count += 1
                    step_name = event.get("name", "step")
                    print(f"   [{step_count}] {step_name}...")
                elif "result" in event:
                    final_result = event["result"]
            
            elapsed = time.time() - start_time
            
            if final_result:
                print("\n" + "-" * 70)
                print(f"⏱️  TIME: {elapsed:.1f}s")
                print(f"🧠 STATE: {final_result['state']}")
                print(f"📊 SCORE: {final_result['final_score']}")
                
                print("\n📝 FINAL ANSWER:\n")
                print(final_result['answer'])
                print("\n" + "-" * 70)
                
                # Simple score check
                if final_result['final_score'] >= tc["min_score"]:
                    print(f"✅ SYSTEM PASS (Score {final_result['final_score']} >= {tc['min_score']})")
                    results["passed"] += 1
                else:
                    print(f"⚠️ LOW SCORE (Score {final_result['final_score']} < {tc['min_score']})")
                    results["failed"] += 1
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results["failed"] += 1
            
    print("\n" + "=" * 70)
    print("HARDCORE TEST COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
