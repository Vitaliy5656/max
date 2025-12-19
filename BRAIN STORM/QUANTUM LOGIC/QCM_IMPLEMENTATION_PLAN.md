# 🚀 План Внедрения QCM: Экстремальный Режим (25 кубитов)

> **Целевая система:** AMD Ryzen 9 5950X / 64GB RAM / RTX 4070 Ti SUPER 16GB  
> **Режим:** EXTREME (25 qubits, GPU acceleration, parallel hypotheses)  
> **Срок:** 6-8 недель  
> **Статус:** ✅ УТВЕРЖДЁН

---

## ✅ Утверждённые Параметры

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| **Бэкенд симуляции** | PennyLane + lightning.gpu | Лучшая интеграция с PyTorch |
| **Количество гипотез** | 7 (параллельно) | Оптимум для 16GB VRAM |
| **Макс. кубитов** | 25 | Экстремальный режим |
| **GPU Memory** | 12GB для QCM | Остаток 4GB для LLM |

> [!WARNING]  
> **Необратимые изменения архитектуры:**
>
> - `HallucinationDetector` → Swap Test
> - `RAGEngine.query()` → альтернативный путь через Quantum Walk

---

## Фаза 0: Подготовка (1-2 дня)

### Новые зависимости

#### [NEW] requirements-quantum.txt

```
# Quantum Simulation Core
pennylane>=0.40.0
pennylane-lightning>=0.40.0
pennylane-lightning-gpu>=0.40.0    # CUDA ускорение

# Tensor Networks (для сжатия 25-кубитных состояний)
tensornetwork>=0.4.6
jax[cuda12]>=0.4.30                 # GPU backend для TensorNetwork

# Optional: NLP to Quantum
lambeq>=0.4.0
discopy>=1.1.0
```

### Конфигурация

#### [NEW] src/core/quantum/config.py

```python
@dataclass
class QCMConfig:
    # Simulation
    max_qubits: int = 25
    device: str = "lightning.gpu"  # or "default.qubit"
    shots: int = 1024
    
    # Hypothesis Generation
    num_hypotheses: int = 7  # ✅ Утверждено пользователем
    parallel_execution: bool = True
    
    # Thresholds
    swap_test_acceptance: float = 0.85
    quantum_walk_steps: int = 10
    
    # Resource Limits
    max_gpu_memory_gb: float = 12.0  # Leave 4GB for LLM
    max_ram_gb: float = 8.0
```

---

## Фаза 1: Квантовая Инфраструктура (1 неделя)

### Модуль квантовой симуляции

#### [NEW] src/core/quantum/**init**.py

```python
from .swap_test import SwapTestVerifier
from .hypothesis import HypothesisGenerator
from .quantum_walk import QuantumWalkSearch
from .middleware import QCMMiddleware

__all__ = [
    "SwapTestVerifier",
    "HypothesisGenerator", 
    "QuantumWalkSearch",
    "QCMMiddleware"
]
```

---

#### [NEW] src/core/quantum/device_manager.py

Управление GPU памятью между LLM и квантовой симуляцией.

```python
class QuantumDeviceManager:
    """Manages quantum simulation devices with GPU memory awareness."""
    
    def __init__(self, config: QCMConfig):
        self.config = config
        self._device = None
        
    async def get_device(self, num_qubits: int):
        """Get appropriate device based on qubit count and available memory."""
        import pennylane as qml
        
        if num_qubits > 20 and self._check_gpu_available():
            return qml.device("lightning.gpu", wires=num_qubits)
        elif num_qubits > 15:
            return qml.device("lightning.qubit", wires=num_qubits)
        else:
            return qml.device("default.qubit", wires=num_qubits)
```

---

## Фаза 2: Ядро QCM (2-3 недели)

### 2.1 Swap Test Верификатор

#### [NEW] src/core/quantum/swap_test.py

**Заменяет:** `hallucination_detector.py` (130 LOC regex → квантовая логика)

```python
import pennylane as qml
from pennylane import numpy as np

class SwapTestVerifier:
    """
    Quantum Swap Test for hypothesis verification.
    
    Replaces regex-based HallucinationDetector with quantum fidelity measurement.
    Uses 25 qubits: 1 control + 12 hypothesis + 12 evidence
    """
    
    def __init__(self, config: QCMConfig):
        self.config = config
        self.num_data_qubits = 12  # 2^12 = 4096 dimensions per register
        self.device = None
        
    async def initialize(self):
        """Initialize quantum device."""
        total_qubits = 1 + 2 * self.num_data_qubits  # 25 qubits
        self.device = qml.device(
            self.config.device,
            wires=total_qubits
        )
        self._build_circuit()
    
    def _build_circuit(self):
        """Build parametrized Swap Test circuit."""
        n = self.num_data_qubits
        
        @qml.qnode(self.device, interface="torch")
        def swap_test_circuit(hypothesis_amplitudes, evidence_amplitudes):
            # Control qubit
            qml.Hadamard(wires=0)
            
            # Encode hypothesis (qubits 1 to n)
            qml.AmplitudeEmbedding(
                features=hypothesis_amplitudes,
                wires=range(1, n+1),
                normalize=True,
                pad_with=0.0
            )
            
            # Encode evidence (qubits n+1 to 2n)
            qml.AmplitudeEmbedding(
                features=evidence_amplitudes,
                wires=range(n+1, 2*n+1),
                normalize=True,
                pad_with=0.0
            )
            
            # Controlled SWAP between registers
            for i in range(n):
                qml.CSWAP(wires=[0, 1+i, n+1+i])
            
            # Final Hadamard
            qml.Hadamard(wires=0)
            
            # Measure control qubit
            return qml.probs(wires=0)
        
        self._circuit = swap_test_circuit
    
    async def verify(
        self, 
        hypothesis_embedding: list[float],
        evidence_embedding: list[float]
    ) -> float:
        """
        Verify hypothesis against evidence using quantum fidelity.
        
        Returns:
            Fidelity score 0.0-1.0 (1.0 = perfect match)
        """
        import torch
        
        # Pad/truncate to 2^n dimensions
        target_dim = 2 ** self.num_data_qubits
        h = self._prepare_amplitudes(hypothesis_embedding, target_dim)
        e = self._prepare_amplitudes(evidence_embedding, target_dim)
        
        # Run quantum circuit
        probs = self._circuit(
            torch.tensor(h, dtype=torch.float64),
            torch.tensor(e, dtype=torch.float64)
        )
        
        # P(|0⟩) = 0.5 + 0.5 * |⟨ψ|φ⟩|²
        # Therefore: fidelity = 2 * P(|0⟩) - 1
        fidelity = float(2 * probs[0] - 1)
        return max(0.0, fidelity)  # Clamp to [0, 1]
```

---

### 2.2 Генератор Гипотез

#### [NEW] src/core/quantum/hypothesis.py

```python
class HypothesisGenerator:
    """
    Generates multiple competing hypotheses from LLM.
    
    Instead of single response, asks LLM for N different answers,
    then uses quantum interference to select the best one.
    """
    
    def __init__(self, lm_client, config: QCMConfig):
        self.lm = lm_client
        self.config = config
        
    async def generate_hypotheses(
        self,
        query: str,
        context: str,
        num_hypotheses: int = 7  # Default: 7 parallel hypotheses
    ) -> list[Hypothesis]:
        """Generate multiple competing hypotheses."""
        
        prompt = f"""Generate {num_hypotheses} DIFFERENT possible answers 
to this question. Each answer should be a distinct interpretation.

Question: {query}
Context: {context}

Format your response as JSON array:
[
  {{"answer": "...", "reasoning": "...", "confidence": 0.0-1.0}},
  ...
]"""
        
        response = await self.lm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return self._parse_hypotheses(response)
```

---

### 2.3 Amplitude Encoding

#### [NEW] src/core/quantum/encoding.py

```python
class AmplitudeEncoder:
    """
    Converts text embeddings to quantum amplitudes.
    
    Uses dimensionality reduction to fit embeddings into 2^n amplitudes.
    """
    
    def __init__(self, target_qubits: int = 12):
        self.target_dim = 2 ** target_qubits
        self._pca = None
        
    async def encode(self, embedding: list[float]) -> np.ndarray:
        """Convert embedding to normalized quantum amplitudes."""
        # Ensure correct dimension
        if len(embedding) != self.target_dim:
            embedding = self._resize(embedding)
        
        # Normalize to unit vector (required for quantum states)
        amplitudes = np.array(embedding, dtype=np.float64)
        norm = np.linalg.norm(amplitudes)
        if norm > 0:
            amplitudes = amplitudes / norm
        
        return amplitudes
```

---

## Фаза 3: Quantum Walk (2 недели)

### 3.1 Quantum Walk по Графу Знаний

#### [NEW] src/core/quantum/quantum_walk.py

**Улучшает:** `rag.py` — добавляет нелокальный поиск

```python
import networkx as nx
from scipy.linalg import expm

class QuantumWalkSearch:
    """
    Quantum Walk on Knowledge Graph for semantic search.
    
    Unlike classical nearest-neighbor, finds structurally important
    nodes through quantum interference of paths.
    """
    
    def __init__(self, config: QCMConfig):
        self.config = config
        self.graph = None
        self._laplacian = None
        
    async def build_graph(self, facts: list[Fact], chunks: list[Chunk]):
        """Build knowledge graph from facts and document chunks."""
        self.graph = nx.Graph()
        
        # Add nodes
        for fact in facts:
            self.graph.add_node(
                f"fact_{fact.id}",
                type="fact",
                content=fact.content,
                embedding=fact.embedding
            )
        
        for chunk in chunks:
            self.graph.add_node(
                f"chunk_{chunk.id}",
                type="chunk", 
                content=chunk.content
            )
        
        # Add edges based on semantic similarity
        await self._connect_similar_nodes()
        
        # Compute graph Laplacian for quantum walk
        self._laplacian = nx.laplacian_matrix(self.graph).toarray()
    
    async def search(
        self,
        query_embedding: list[float],
        evolution_time: float = 1.0,
        top_k: int = 5
    ) -> list[SearchResult]:
        """
        Perform quantum walk search.
        
        Args:
            query_embedding: Query vector
            evolution_time: Walk duration (controls spread)
            top_k: Number of results
            
        Returns:
            Nodes ranked by quantum hitting probability
        """
        n = len(self.graph.nodes)
        
        # Initialize walker at query-similar nodes
        psi_0 = await self._init_state(query_embedding)
        
        # Unitary evolution: U(t) = exp(-iLt)
        U = expm(-1j * self._laplacian * evolution_time)
        
        # Evolve state
        psi_t = U @ psi_0
        
        # Probability distribution
        probs = np.abs(psi_t) ** 2
        
        # Return top-k nodes
        top_indices = np.argsort(probs)[-top_k:][::-1]
        
        return [
            SearchResult(
                node_id=list(self.graph.nodes)[i],
                probability=probs[i],
                content=self.graph.nodes[list(self.graph.nodes)[i]]["content"]
            )
            for i in top_indices
        ]
```

---

## Фаза 4: Интеграция (1-2 недели)

### 4.1 QCM Middleware Оркестратор

#### [NEW] src/core/quantum/middleware.py

```python
class QCMMiddleware:
    """
    Quantum-Cognitive Middleware - центральный оркестратор.
    
    Координирует:
    - Hypothesis Generation
    - Quantum Walk Search  
    - Swap Test Verification
    - Wave Function Collapse (final selection)
    """
    
    def __init__(
        self,
        lm_client,
        memory_manager,
        rag_engine,
        config: QCMConfig
    ):
        self.lm = lm_client
        self.memory = memory_manager
        self.rag = rag_engine
        self.config = config
        
        # Quantum components
        self.hypothesis_gen = HypothesisGenerator(lm_client, config)
        self.swap_test = SwapTestVerifier(config)
        self.quantum_walk = QuantumWalkSearch(config)
        self.encoder = AmplitudeEncoder()
        
    async def initialize(self):
        """Initialize all quantum components."""
        await self.swap_test.initialize()
        
    async def process(
        self,
        query: str,
        conversation_id: str
    ) -> QCMResult:
        """
        Main QCM processing pipeline.
        
        1. Generate hypotheses (LLM)
        2. Search evidence (Quantum Walk)
        3. Verify each hypothesis (Swap Test)
        4. Collapse to best answer
        """
        # 1. Get context
        context = await self.memory.get_smart_context(conversation_id)
        
        # 2. Generate competing hypotheses
        hypotheses = await self.hypothesis_gen.generate_hypotheses(
            query=query,
            context=context,
            num_hypotheses=self.config.num_hypotheses
        )
        
        # 3. Build knowledge graph and search
        facts = await self.memory.get_relevant_facts(query)
        chunks = await self.rag.query(query, top_k=20)
        await self.quantum_walk.build_graph(facts, chunks)
        evidence = await self.quantum_walk.search(
            query_embedding=await self.lm.get_embedding(query),
            top_k=10
        )
        
        # 4. Verify each hypothesis against evidence
        evidence_embedding = await self._combine_evidence(evidence)
        
        scores = []
        for hyp in hypotheses:
            hyp_embedding = await self.lm.get_embedding(hyp.answer)
            fidelity = await self.swap_test.verify(
                hypothesis_embedding=hyp_embedding,
                evidence_embedding=evidence_embedding
            )
            scores.append((hyp, fidelity))
        
        # 5. Wave Function Collapse - select winner
        best_hypothesis, best_score = max(scores, key=lambda x: x[1])
        
        return QCMResult(
            answer=best_hypothesis.answer,
            confidence=best_score,
            evidence_used=evidence,
            all_hypotheses=hypotheses,
            verification_scores=scores
        )
```

---

### 4.2 Интеграция с Chat API

#### [MODIFY] src/api/routers/chat.py

```diff
+ from src.core.quantum import QCMMiddleware, QCMConfig

  async def chat_endpoint(...):
+     # Check if QCM is enabled for this query
+     if should_use_qcm(query, user_preferences):
+         qcm = QCMMiddleware(lm_client, memory, rag, QCMConfig())
+         result = await qcm.process(query, conversation_id)
+         return ChatResponse(
+             content=result.answer,
+             qcm_confidence=result.confidence,
+             qcm_evidence=result.evidence_used
+         )
      
      # Fallback to classical path
      return await classical_chat(...)
```

---

## План Верификации

### Автоматические Тесты

```python
# tests/quantum/test_swap_test.py
async def test_swap_test_identical_states():
    """Identical states should have fidelity ~1.0"""
    verifier = SwapTestVerifier(QCMConfig())
    await verifier.initialize()
    
    embedding = [0.5, 0.5, 0.5, 0.5]  # Simplified
    fidelity = await verifier.verify(embedding, embedding)
    
    assert fidelity > 0.95

async def test_swap_test_orthogonal_states():
    """Orthogonal states should have fidelity ~0.0"""
    verifier = SwapTestVerifier(QCMConfig())
    await verifier.initialize()
    
    emb1 = [1.0, 0.0, 0.0, 0.0]
    emb2 = [0.0, 1.0, 0.0, 0.0]
    fidelity = await verifier.verify(emb1, emb2)
    
    assert fidelity < 0.1
```

### Ручная Верификация

1. Сравнить качество ответов с/без QCM на 100 тестовых вопросах
2. Измерить latency для разных размеров кубитов
3. Проверить GPU memory usage под нагрузкой

---

## Временная Оценка

| Фаза | Задачи | Срок |
|------|--------|------|
| 0 | Установка зависимостей, конфиг | 1-2 дня |
| 1 | Device Manager, базовые тесты | 1 неделя |
| 2 | Swap Test, Hypothesis Gen, Encoding | 2-3 недели |
| 3 | Quantum Walk, интеграция с RAG | 2 недели |
| 4 | Middleware, API, финальные тесты | 1-2 недели |

**Итого: 6-8 недель** при работе 3-4 часа/день
