# MAX AI Assistant

**MAX (Modular AI Xperience)** is a next-generation AI assistant capable of autonomous task execution, context-aware adaptation, and multimodal interaction.

## 🚀 Features

- **Thinking System**: Visible thought process utilizing `<think>` tags from reasoning models.
- **Autonomous Agent**: AutoGPT-based agent for complex multi-step tasks.
- **IQ & EQ Metrics**: Real-time tracking of intelligence and empathy scores based on interaction quality.
- **RAG & Memory**: Context-aware responses using semantic search and long-term memory.
- **Modular Design**: React (Vite) frontend + FastAPI backend.

## 🛠️ Stack

- **Frontend**: React 19, TypeScript, TailwindCSS, Lucide Icons, Vite.
- **Backend**: Python 3.12, FastAPI, SQLite (aiosqlite).
- **AI Core**: LM Studio Integration (Local LLMs), OpenAI API compatible.

## 🏁 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- LM Studio (running locally on port 1234)

### Installation

1. **Backend Setup**:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Setup**:

   ```bash
   cd frontend
   npm install
   ```

3. **Running**:
   - Start Backend: `run_api.bat` (or `python run.py`)
   - Start Frontend: `run_ui.bat` (or `cd frontend && npm run dev`)

## 🧪 Testing

```bash
# Backend Tests
python -m pytest tests/

# Frontend Tests
cd frontend && npm test
```

## 📂 Project Structure

- `src/core`: Core AI logic (Agent, Memory, Rag, LM Client).
- `src/api`: FastAPI routers and endpoints.
- `frontend/src`: React application.
- `MIND/`: Documentation and project logs.

## 📄 License

MIT License.
