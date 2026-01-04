# 🏗️ MAX ENGINE: PROTOTYPE IMPLEMENTATION PLAN

**Goal:** Build the initial `MAX Engine` prototype — a custom high-performance inference server based on `ExLlamaV2` that enables "Cognitive Orchestration" (Small Model steering Big Model).

## User Review Required
>
> [!IMPORTANT]
> **Hardware Requirement**: This implementation strictly requires an NVIDIA GPU (RTX 30xx/40xx recommended) with at least 12GB VRAM (ideally 16GB) to load both models.
> **Dependency**: `exllamav2` requires CUDA toolkit installed.

## Proposed Changes

We will create a new distinct module `src/max_engine` to avoid polluting the existing codebase until the prototype is proven.

### 1. 📂 Core Engine (`src/max_engine/core/`)

#### [NEW] [model_wrapper.py](file:///src/max_engine/core/model_wrapper.py)

* **Purpose**: Wrapper around `ExLlamaV2` that exposes the `manual_forward` capability.
* **Key Features**:
  * `load_model(dir)`
  * `forward_surgical(input_ids, steering_vectors)`: The custom loop that iterates `model.modules` and applies injections.

#### [NEW] [steering.py](file:///src/max_engine/core/steering.py)

* **Purpose**: Manages vectors.
* **Key Features**:
  * `SteeringController` class.
  * `register_hook(layer, vector, coeff)`
  * `get_active_vectors(layer)`

#### [NEW] [orchestrator.py](file:///src/max_engine/core/orchestrator.py)

* **Purpose**: The main "Game Loop" of generation.
* **Key Features**:
  * `generate()`: Async generator.
  * Implements the "Intervention Loop": `BigModel -> Logits -> SmallModel -> Decision -> (Steer?) -> Sample`.

### 2. 🔌 API Layer (`src/max_engine/server/`)

#### [NEW] [api.py](file:///src/max_engine/server/api.py)

* **Purpose**: FastAPI server compatible with OpenAI Chat Completions.
* **Key Features**:
  * `POST /v1/chat/completions`
  * Streaming response support (SSE).

### 3. 🛠️ Utilities

#### [NEW] [verify_env.py](file:///src/max_engine/verify_env.py)

* Simple script to check if `exllamav2` is importable and GPU is accessible.

## Verification Plan

### Automated Tests

* **Unit Test**: `tests/max_engine/test_steering.py`
  * Mock the generic tensor operations to verify the math (`hidden_state += vector`).
* **Integration Test**: `tests/max_engine/test_loop.py`
  * Load a tiny model (e.g., Qwen-0.5B) if available, or just mock the `ExLlamaV2` class to verify the *logic flow* of the orchestrator without needing full VRAM.

### Manual Verification

1. **Environment Check**: Run `python src/max_engine/verify_env.py`.
2. **Injection Test**:
    * Run a script that generates text with a specific "Steering Vector" (e.g., a random noise vector) and confirm the output changes compared to a clean run.
    * *Command*: `python src/max_engine/scripts/test_injection.py`
