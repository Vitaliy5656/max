# 🏗️ MAX ENGINE: АРХИТЕКТУРА (DESIGN DOCUMENT)

**Версия:** 1.0
**Целевое железо:** RTX 4070 Ti Super (16GB VRAM)
**Базовая библиотека:** `ExLlamaV2` (Python/CUDA/C++)

---

## 1. 📦 ЗАВИСИМОСТИ (DEPENDENCIES)

Необходимые Python пакеты для окружения.

```txt
# Core Inference (Ядро инференса)
exllamav2>=0.0.12      # Самый быстрый движок для Llama/Qwen на 40xx
torch>=2.2.0           # PyTorch для тензорных операций
numpy

# API & Server (Серверная часть)
fastapi                # Современный Async API фреймворк
uvicorn                # ASGI сервер для запуска FastAPI
pydantic               # Валидация данных

# Vector Management (Базы данных векторов)
sqlite-vec             # Хранение steering-векторов (векторов направления)
sqlite3                # Драйвер базы данных

# Utilities
websockets             # Для real-time стриминга (опционально)
aiohttp                # Асинхронный HTTP клиент
```

---

## 2. ⚙️ ОБЗОР АРХИТЕКТУРЫ

Система использует **Unified-Process** (Единый процесс) архитектуру. Учитывая жесткое ограничение в 16GB VRAM, это критически важно: Большая и Малая модели должны жить в одном Python-процессе, чтобы делить видеопамять (Zero-copy) и передавать тензоры без копирования через CPU.

### Раскладка памяти (Цель: 16GB VRAM)

* **Big Model (Qwen-2.5-7B-Instruct-GPTQ-Int4 / EXL2)**: ~5.0 GB
* **Small Model (Qvikhr-1.5B-Instruct-EXL2)**: ~1.5 GB
* **KV Cache (Shared/Paged)**: ~8.0 GB (Динамическое выделение через Paged Attention)
* **Overhead (Буферы CUDA, PyTorch)**: ~1.5 GB

### Концепция "Общего Контекста" (Context Mirror)

Так как Qwen и Qvikhr имеют разную архитектуру (размер скрытого слоя, количество слоев), они **не могут** физически использовать один и тот же KV Cache.
**Решение:** `ContextMirror` (Зеркало Контекста). Оркестратор хранит *Последовательность Токенов*. Обе модели обрабатывают одни и те же входные токены. Малая модель "принудительно" синхронизируется с Большой: как только Большая рождает токен, он скармливается Малой.

* **"Взгляд на логиты"**: Малая модель делает forward pass (проход) по текущему контексту и может "подсмотреть" логиты Большой модели, чтобы вынести суждение (остановить? вмешаться?).

---

## 3. 🏗️ СТРУКТУРА КЛАССОВ (PYTHON)

### A. `SteeringController` (Контроллер вмешательства)

Управляет "Нейрохирургией". Хранит векторы и отвечает за математику инъекций.

```python
import torch
import numpy as np

class SteeringController:
    """
    Управляет векторами направлений (steering vectors) и их внедрением в модель.
    """
    def __init__(self, device="cuda"):
        self.vectors = {}  # {'sadness': torch.Tensor, ...}
        self.active_hooks = []
        self.device = device

    def load_vector(self, name: str, vector_data: np.ndarray):
        """Загрузка вектора из БД в VRAM."""
        tensor = torch.from_numpy(vector_data).to(self.device).half()
        self.vectors[name] = tensor

    def get_injection(self, layer_idx: int) -> torch.Tensor | None:
        """Расчет комбинированного вектора для конкретного слоя."""
        # Суммируем активные векторы для этого слоя
        # Возвращаем None, если вмешательство не нужно
        pass
```

### B. `ExLlamaEngine` (Обертка)

Обертка вокруг `ExLlamaV2`, позволяющая итерироваться по слоям вручную (чтобы вставлять хуки).

```python
from exllamav2 import ExLlamaV2, ExLlamaV2Config, ExLlamaV2Cache, ExLlamaV2Tokenizer

class ExLlamaEngine:
    def __init__(self, model_dir: str, max_seq_len: int = 8192):
        self.config = ExLlamaV2Config()
        self.config.model_dir = model_dir
        self.config.prepare()
        
        self.model = ExLlamaV2(self.config)
        self.cache = ExLlamaV2Cache(self.model, max_seq_len=max_seq_len)
        self.tokenizer = ExLlamaV2Tokenizer(self.config)
        
        self.model.load_autosplit(self.cache)

    def forward_with_steering(self, 
                            input_ids: torch.Tensor, 
                            steering_controller: SteeringController):
        """
        Кастомный проход (forward pass), который итерируется по слоям для инъекций.
        """
        # Это "Хирургический" проход
        # 1. Эмбеддинги
        hidden_states = self.model.modules[0].forward(input_ids, self.cache)
        
        # 2. Итерация по слоям трансформера
        for i, layer in enumerate(self.model.modules[1:], start=1):
            
            # A. Проверка на инъекцию (Хук)
            injection = steering_controller.get_injection(layer_idx=i)
            if injection is not None:
                hidden_states += injection * 0.5  # коэффициент силы
            
            # B. Стандартный проход слоя
            # Важно: сигнатура может отличаться в разных версиях ExLlamaV2
            hidden_states = layer.forward(hidden_states, self.cache, ...)
            
        return hidden_states
```

### C. `CognitiveOrchestrator` (Дирижер)

Главный цикл генерации. Управляет обеими моделями.

```python
class CognitiveOrchestrator:
    def __init__(self, big_model: ExLlamaEngine, small_model: ExLlamaEngine):
        self.big_model = big_model
        self.small_model = small_model
        self.steering = SteeringController()

    async def generate_orchestrated(self, prompt: str):
        # 1. Prefill (заполнение контекста) обеих моделей
        ids = self.big_model.tokenizer.encode(prompt)
        self.big_model.prefill(ids)
        self.small_model.prefill(ids)

        stop_condition = False
        while not stop_condition:
            # 2. Шаг Большой Модели (Получаем Логиты - предсказания)
            big_logits = self.big_model.forward_step()
            
            # 3. Суд Малой Модели
            # Малая модель смотрит на контекст и (опционально) на планы Большой
            # decision = self.small_model.judge(big_logits, context)
            
            decision = self.decide_action(big_logits) 
            
            if decision == "STEER":
                # Применяем вектор и перезапускаем шаг Большой модели
                self.steering.activate("logic_boost", layer=15)
                big_logits = self.big_model.forward_step_with_steering(self.steering)
            
            # 4. Сэмплинг (Выбор токена) и выдача
            token = self.sample(big_logits)
            
            # Синхронизируем KV-кэш Малой модели с выбранным токеном
            self.small_model.update_cache(token)
            
            yield token
            
            if token == self.big_model.tokenizer.eos_token_id:
                stop_condition = True
```

---

## 4. 🧬 ПРИМЕР: ВНЕДРЕНИЕ ВЕКТОРА В EXLLAMAV2

Пример того, как реально внедрить вектор в `ExLlamaV2`, обходя оптимизированные fused-ядра и запуская слои вручную. Python-цикл работает медленнее (на 10-15%), но позволяет делать "магию".

```python
import torch
from exllamav2 import ExLlamaV2, ExLlamaV2Config, ExLlamaV2Cache

# Загрузка модели
config = ExLlamaV2Config()
config.model_dir = "models/Qwen2.5-7B-Instruct-exl2"
config.prepare()

model = ExLlamaV2(config)
cache = ExLlamaV2Cache(model, lazy=True)
model.load_autosplit(cache)

# --- ДАННЫЕ ДЛЯ ВМЕШАТЕЛЬСТВА ---
# Размер вектора должен совпадать с hidden_size (напр., 4096 для 7B)
steering_vector = torch.load("vectors/creativity_v1.pt").to("cuda").half()
target_layer_idx = 15
steering_coeff = 1.5

def surgical_forward(input_ids, cache, last_id_only=True):
    """
    Ручной forward pass для возможности инъекции.
    """
    # 1. Обработка входных эмбеддингов
    hidden_state = model.modules[0].forward(input_ids)

    # 2. Итерация через слои Трансформера
    # model.modules содержит [Embeddings, Layer0, Layer1, ..., Norm, Head]
    for i, module in enumerate(model.modules[1:-2]): # Пропускаем emb, norm, head
        layer_idx = i
        
        # --- ТОЧКА ВМЕШАТЕЛЬСТВА (INJECTION POINT) ---
        if layer_idx == target_layer_idx:
            # Добавляем вектор к скрытому состоянию
            hidden_state += steering_vector * steering_coeff
        # ---------------------------------------------
        
        # Запуск слоя
        hidden_state = module.forward(hidden_state, cache, attention_mask=None)

    # 3. Финальная нормализация и Голова (Head)
    hidden_state = model.modules[-2].forward(hidden_state) # RMSNorm
    logits = model.modules[-1].forward(hidden_state)       # Head
    
    return logits
```

---

## 5. 🔌 API СЛОЙ (FastAPI)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

app = FastAPI()
# orchestrator = CognitiveOrchestrator(...)

class ChatRequest(BaseModel):
    messages: list
    model: str = "max-orchestrator"

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    # Логика конвертации сообщений в промпт...
    prompt = "converted_prompt"
    
    async def stream_generator():
        # async for token in orchestrator.generate_orchestrated(prompt):
        #     yield f"data: {json.dumps({'choices': [{'delta': {'content': token}}]})}\n\n"
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(stream_generator(), media_type="text/event-stream")
```

---

## 6. ⚔️ КОНКУРЕНТНЫЙ АНАЛИЗ: MAX vs LM STUDIO (ИССЛЕДОВАНИЕ 2026)

Наше исследование LM Studio (v0.3.x / Roadmap 2026) выявило критические ограничения, которые **MAX Engine** позволяет преодолеть.

| Функция | LM Studio (2026) | 🏗️ MAX Engine (Наш) |
| :--- | :--- | :--- |
| **Движок (Core)** | `llama.cpp` (GGUF) / MLX | **`ExLlamaV2` (EXL2)** |
| **Скорость (4070 Ti)** | Хорошая, но редко нагружает CUDA на 100% | **SOTA** (Максимально оптимизированные C++ ядра) |
| **Мульти-модель** | Только параллельная загрузка. API вызовы отдельные. | **Внутрипроцессная Оркестрация**. Zero-copy обмен тензорами. |
| **Вмешательство** | **Нет**. API — "черный ящик". | **Глубокая Хирургия**. Хуки на конкретные слои (напр., Layer 15). |
| **Задержка (Latency)** | +20ms на каждый HTTP вызов (Localhost) | **In-Memory** (<1ms цикл проверки) |
| **Steering (Управление)** | Не поддерживается. | **Нативное**. `hidden_states += vector`. |
| **Квантование** | GGUF (Смешанное CPU/GPU) | **EXL2 (4-bit)**. Создано специально для чистого GPU. |

### 🚀 ПОЧЕМУ MAX ПОБЕЖДАЕТ

1. **Задержка "Дирижера"**: В LM Studio, если мы захотим сделать Python-скрипт "оркестратор", мы будем платить цену HTTP-запроса (Сериализация -> Отправка -> Инференс -> Прием -> Десериализация) *на каждом токене*. MAX Engine запускает оркестрацию в **том же Python-процессе**, где крутятся CUDA ядра. Малая модель читает тензоры Большой модели напрямую из VRAM без копирования в оперативную память.
2. **Настоящая Нейрохирургия**: LM Studio — это черный ящик. Вы не можете сказать "Добавь этот вектор к слою 15" через их API. MAX Engine дает нам прямой доступ к объекту `model.modules` из Python.
3. **Утилизация VRAM**: LM Studio — это комбайн "для всех", она часто консервативно использует память. MAX Engine **жестко заточен** под наш бюджет в 16GB VRAM, позволяя впихнуть `Qwen-7B` + `Qvikhr-1.5B` + `ContextMirror` с точностью до мегабайта благодаря EXL2 квантованию.
