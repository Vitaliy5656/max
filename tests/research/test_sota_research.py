import asyncio
import os
import json
from src.core.research.deep_research import DeepResearchAgent, RunStatus
from src.core.memory import memory

import sys

# Фикс для кодировки Windows консоли
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    print("START: Запуск SOTA Deep Research Test (CLI Mode)")
    print("-" * 50)
    
    # Инициализация базы данных памяти
    await memory.initialize()
    agent = DeepResearchAgent(memory._db)
    await agent.initialize(memory._db)
    
    goal = "История клавиатуры и мыши: от изобретения до наших дней, ключевые вехи развития"
    print(f"GOAL: Цель: {goal}")
    print("[TEST] NEW TOPIC - keyboard & mouse history - to verify full cycle")
    
    # 1. Планирование (Editable CoT)
    run = await agent.set_goal(goal, max_steps=10, use_editable_cot=True)
    print("\n[PLANNER] Генерация плана...")
    
    # Запускаем генератор, чтобы дойти до подтверждения плана
    gen = agent.run_generator()
    try:
        async for step in gen:
            if step.action == "plan_created":
                print(f"\nPLAN: ПЛАН СОЗДАН:")
                for i, task in enumerate(run.plan, 1):
                    print(f"  {i}. {task.description}")
                break
    finally:
        await gen.aclose()
            
    # В реальном UI пользователь бы нажал "Confirm". Здесь подтверждаем программно.
    print("\n[USER] Подтверждаю план. Начинаю выполнение...")
    run.status = RunStatus.RUNNING
    
    # 2. Исполнение и проверка
    async for step in agent.run_generator():
        print(f"\n--- Шаг {step.step_number}: {step.action} ---")
        if step.action == "web_search":
            print(f"SEARCH: Поиск: {step.action_input.get('query')}")
        elif step.action == "read_webpage":
            print(f"READ: Чтение: {step.action_input.get('url')}")
        elif step.action == "save_knowledge":
            print(f"FACT: Факт: {step.result}")
            
        if run.status == RunStatus.FAILED:
            break
            
    print("\n" + "="*50)
    print("FINISH: ИССЛЕДОВАНИЕ ЗАВЕРШЕНО")
    if run.result:
        print("\nREPORT: ИТОГОВЫЙ ОТЧЕТ (СИНТЕЗ):")
        print(run.result)
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
