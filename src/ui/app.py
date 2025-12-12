"""
Gradio UI Application for MAX AI Assistant.

⚠️ LEGACY UI: This is the original Gradio interface.
The primary UI is now React (frontend/src/App.tsx).
This file is kept as a fallback for when React is unavailable.

Consider using: python main.py → http://localhost:5173

Features:
- Chat interface with streaming
- Model switcher
- Templates/Prompts panel
- RAG documents panel
- Auto-GPT tasks panel
- Search history
- Settings panel
- Dark theme
"""
import asyncio
import uuid
from typing import Optional, Generator
from pathlib import Path

import gradio as gr

from ..core.config import config
from ..core.lm_client import lm_client, TaskType
from ..core.memory import memory, Conversation
from ..core.user_profile import user_profile, Verbosity, Formality
from ..core.tools import tools, TOOLS
from ..core.web_search import web_searcher
from ..core.rag import rag
from ..core.autogpt import autogpt, RunStatus
from ..core.templates import templates
from ..core.speech import speech
from ..core.metrics import metrics_engine
from ..core.adaptation import (
    initialize_adaptation, prompt_builder, correction_detector,
    anticipation_engine
)


class MaxAssistantUI:
    """
    Main Gradio application for MAX AI Assistant.
    """
    
    def __init__(self):
        self.current_conversation: Optional[Conversation] = None
        self._initialized = False
        # P0 Fix: Security state for dangerous actions
        self.allow_dangerous = False
        # Logic Fix: Track pending message for feedback analysis
        self._pending_feedback_msg_id: Optional[int] = None
        
    async def initialize(self):
        """Initialize all subsystems."""
        if self._initialized:
            return
            
        await memory.initialize()
        await user_profile.initialize(memory._db)
        await rag.initialize(memory._db)
        await autogpt.initialize(memory._db)
        # P0 Fix: Register security callback
        autogpt.set_callbacks(on_confirmation_needed=self._security_check)
        await templates.initialize(memory._db)
        
        # IQ & Empathy metrics system
        await metrics_engine.initialize(memory._db)
        await initialize_adaptation(memory._db)
        
        self._initialized = True
        
        # P0 Fix: Load security preference
        if user_profile.preferences:
             self.allow_dangerous = user_profile.preferences.allow_dangerous
        
        # Create initial conversation
        self.current_conversation = await memory.create_conversation("Новый разговор")
    
    async def chat(
        self,
        message: str,
        history: list,
        model_choice: str,
        temperature: float,
        reasoning_mode: bool,
        use_rag: bool
    ) -> Generator:
        """Process chat message with streaming response."""
        if not self._initialized:
            await self.initialize()
        
        if not message.strip():
            yield history
            return
        
        # Logic Fix: Analyze current message as feedback on PREVIOUS response
        if self._pending_feedback_msg_id:
            await metrics_engine.record_interaction_outcome(
                message_id=self._pending_feedback_msg_id,
                user_message=message,  # This IS the reaction to previous response
                facts_in_context=0,
                style_prompt_length=0
            )
            self._pending_feedback_msg_id = None
        
        # Track interaction for personalization
        await user_profile.track_interaction(message)
        await user_profile.detect_mood(message)
        
        # Add user message to memory
        await memory.add_message(
            self.current_conversation.id,
            "user",
            message
        )
        
        # Build context with smart memory
        context = await memory.get_smart_context(
            self.current_conversation.id,
            max_tokens=config.memory.max_context_tokens
        )
        
        # Add RAG context if enabled
        if use_rag:
            rag_context = await rag.get_context_for_query(message)
            if rag_context:
                context.insert(0, {"role": "system", "content": rag_context})
        
        # Add adaptive style prompt (learns from patterns)
        base_style = user_profile.get_style_prompt()
        adaptive_prompt = await prompt_builder.build_adaptive_prompt(
            base_style_prompt=base_style,
            include_corrections=True,
            include_successes=True
        )
        if adaptive_prompt:
            context.insert(0, {"role": "system", "content": adaptive_prompt})
        
        # Track style prompt length for metrics
        style_prompt_length = len(adaptive_prompt) if adaptive_prompt else 0
        
        # Add system prompt
        system_prompt = """Ты MAX — умный локальный ИИ-ассистент. 
Ты можешь:
- Отвечать на вопросы и вести диалог
- Работать с файлами на компьютере пользователя
- Искать информацию в интернете
- Помнить предыдущие разговоры
- Подстраиваться под стиль общения пользователя
- Использовать загруженные документы для ответов

Отвечай на языке пользователя. Будь полезным и дружелюбным."""
        
        context.insert(0, {"role": "system", "content": system_prompt})
        context.append({"role": "user", "content": message})
        
        # Determine task type
        task_type = TaskType.REASONING if reasoning_mode else lm_client.detect_task_type(message)
        
        # Select model
        model = model_choice if model_choice != "auto" else lm_client.get_model_for_task(task_type)
        
        # Get streaming response
        history = history + [[message, ""]]
        
        try:
            full_response = ""
            async for chunk in await lm_client.chat(
                messages=context,
                model=model,
                stream=True,
                temperature=temperature,
                task_type=task_type,
                tools=TOOLS if not reasoning_mode else None
            ):
                full_response += chunk
                history[-1][1] = full_response
                yield history
            
            saved_msg = await memory.add_message(
                self.current_conversation.id,
                "assistant",
                full_response,
                model_used=model
            )
            
            # Logic Fix: Store message ID to analyze USER's NEXT message as feedback
            if saved_msg:
                self._pending_feedback_msg_id = saved_msg.id
            
            # Save daily metrics periodically
            if user_profile.habits and user_profile.habits.total_interactions % 20 == 0:
                await metrics_engine.save_daily_metrics()
            
        except Exception as e:
            history[-1][1] = f"Error: {str(e)}"
            yield history
    
    async def new_conversation(self):
        """Start a new conversation."""
        if not self._initialized:
            await self.initialize()
        self.current_conversation = await memory.create_conversation("Новый разговор")
        return [], f"Новый разговор: {self.current_conversation.id[:8]}"
    
    async def search_history(self, query: str) -> list:
        """Search across all conversations."""
        if not self._initialized:
            await self.initialize()
        if not query.strip():
            return []
        results = await memory.search_history(query, limit=20)
        return [[r.conversation_id[:8], r.role, r.content[:100] + "..."] for r in results]
    
    async def load_conversation_from_history(self, evt: gr.SelectData, search_results: list):
        """Load selected conversation from history."""
        # Get row index
        index = evt.index[0]
        row = search_results.iloc[index] if hasattr(search_results, "iloc") else search_results[index]
        short_id = row[0]
        
        # Find full ID (inefficient but safe)
        # In real app we should store full ID hidden
        convs = await memory.list_conversations(limit=100)
        conv = next((c for c in convs if c.id.startswith(short_id)), None)
        
        if conv:
            self.current_conversation = conv
            # Get messages for chat
            messages = await memory.get_messages(conv.id)
            history = []
            for msg in messages:
                if msg.role == "user":
                    history.append([msg.content, ""])
                elif msg.role == "assistant":
                    if history:
                        history[-1][1] = msg.content
                    else:
                        # Orphaned assistant message?
                        history.append(["", msg.content])
            
            return history, f"Загружен разговор: {short_id}"
        
        return [], "Разговор не найден"
    
    async def get_available_models(self) -> list:
        """Get list of available models with error handling."""
        try:
            models = await lm_client.list_models()
            model_ids = ["auto"] + [m.id for m in models]
        except Exception as e:
            # LAZY IMPL FIX: Fallback when LM Studio unavailable
            print(f"Warning: Failed to fetch models from LM Studio: {e}")
            model_ids = ["auto"]
        return gr.Dropdown(choices=model_ids, value="auto")
    
    async def save_feedback(self, rating: int, history: list):
        """Save user feedback on last response."""
        if not history:
            return "Нет сообщений"
        messages = await memory.get_messages(self.current_conversation.id, limit=1)
        if messages:
            await user_profile.record_feedback(messages[-1].id, positive=(rating > 0))
        return "Спасибо!"
    
    # ==================== Voice Input ====================
    
    async def transcribe_audio(self, audio):
        """Transcribe audio to text."""
        if audio is None:
            return ""
        try:
            result = await speech.transcribe(audio)
            return result.text
        except Exception as e:
            return f"[Ошибка транскрипции: {str(e)}]"
    
    # ==================== RAG Methods ====================
    
    async def upload_document(self, file):
        """Upload and index a document."""
        if not self._initialized:
            await self.initialize()
        if not file:
            return "Выберите файл", await self.list_documents()
        try:
            doc = await rag.add_document(file.name)
            return f"Добавлен: {doc.filename} ({doc.chunk_count} chunks)", await self.list_documents()
        except Exception as e:
            return f"Ошибка: {str(e)}", await self.list_documents()
    
    async def list_documents(self):
        """List all indexed documents."""
        if not self._initialized:
            await self.initialize()
        docs = await rag.list_documents()
        return [[d.filename, d.file_type, d.chunk_count, d.id[:8]] for d in docs]
    
    async def delete_document(self, doc_id: str):
        """Delete a document."""
        if not self._initialized:
            await self.initialize()
        # Find full ID
        docs = await rag.list_documents()
        doc = next((d for d in docs if d.id.startswith(doc_id)), None)
        if doc:
            await rag.remove_document(doc.id)
            return "Удалено", await self.list_documents()
        return "Не найдено", await self.list_documents()
    
    # ==================== AutoGPT Methods ====================
    
    async def _security_check(self, action: str, inputs: dict) -> bool:
        """P0 Fix: Security callback for dangerous tools."""
        return self.allow_dangerous

    async def start_autogpt(self, goal: str, max_steps: int) -> Generator:
        """Start an Auto-GPT run (Non-blocking generator)."""
        if not self._initialized:
            await self.initialize()
        if not goal.strip():
            yield "Введите цель", []
            return
        
        try:
            run = await autogpt.set_goal(goal, max_steps=int(max_steps))
            
            steps_data = []
            yield f"Status: {run.status.value}", steps_data
            
            # P1 Fix: Consume generator for non-blocking UI updates
            async for step in autogpt.run_generator():
                steps_data.append([
                    step.step_number, 
                    step.action, 
                    step.result[:200] + "..." if step.result and len(step.result) > 200 else (step.result or "")
                ])
                yield f"Running step {step.step_number}...", steps_data
            
            final_status = f"Status: {run.status.value}"
            if run.status == RunStatus.FAILED:
                final_status += f" ({run.result})"
            
            yield final_status, steps_data
            
        except Exception as e:
            yield f"Error: {str(e)}", []
    
    async def list_autogpt_runs(self):
        """List past Auto-GPT runs."""
        if not self._initialized:
            await self.initialize()
        runs = await autogpt.list_runs(limit=10)
        return [[r.id[:8], r.goal[:50], r.status.value, r.current_step] for r in runs]
    
    # ==================== Templates Methods ====================
    
    async def list_templates(self):
        """List all templates."""
        if not self._initialized:
            await self.initialize()
        tpls = await templates.list_all()
        return [[t.name, t.category or "-", t.use_count, t.id[:8]] for t in tpls]
    
    async def use_template(self, template_id: str, variables: str):
        """Use a template with variables."""
        if not self._initialized:
            await self.initialize()
        try:
            # Find full ID
            all_tpls = await templates.list_all()
            tpl = next((t for t in all_tpls if t.id.startswith(template_id)), None)
            if not tpl:
                return "Шаблон не найден"
            
            # Parse variables (simple key=value format)
            vars_dict = {}
            for line in variables.strip().split('\n'):
                if '=' in line:
                    key, val = line.split('=', 1)
                    vars_dict[key.strip()] = val.strip()
            
            result = await templates.use(tpl.id, vars_dict)
            return result
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    async def add_template(self, name: str, prompt: str, category: str):
        """Add a new template."""
        if not self._initialized:
            await self.initialize()
        if not name or not prompt:
            return "Заполните имя и промпт", await self.list_templates()
        await templates.add(name, prompt, category=category or None)
        return "Шаблон добавлен", await self.list_templates()
    
    def build_ui(self) -> gr.Blocks:
        """Build the Gradio interface."""
        
        with gr.Blocks(
            title="MAX AI Assistant",
            theme=gr.themes.Soft(primary_hue="blue"),
            css=".chat-container { height: 60vh !important; }"
        ) as app:
            
            gr.Markdown("# 🤖 MAX AI Assistant")
            gr.Markdown("*Локальный ИИ-ассистент с памятью, RAG и Auto-GPT*")
            
            with gr.Tabs():
                # ==================== Chat Tab ====================
                with gr.TabItem("💬 Чат"):
                    with gr.Row():
                        with gr.Column(scale=4):
                            chatbot = gr.Chatbot(label="Диалог", height=450)
                            
                            with gr.Row():
                                msg = gr.Textbox(label="Сообщение", placeholder="Напишите или запишите голос...", lines=2, scale=4)
                                audio_input = gr.Audio(label="🎤", sources=["microphone"], type="filepath", scale=1)
                                send_btn = gr.Button("📤", scale=1, variant="primary")
                            
                            with gr.Row():
                                gr.Button("👍", scale=1).click(self.save_feedback, [gr.Number(1, visible=False), chatbot], gr.Textbox())
                                gr.Button("👎", scale=1).click(self.save_feedback, [gr.Number(-1, visible=False), chatbot], gr.Textbox())
                                new_btn = gr.Button("🆕 Новый", scale=2)
                        
                        with gr.Column(scale=1):
                            status = gr.Textbox(label="Статус", value="Готов", interactive=False)
                            model_dropdown = gr.Dropdown(label="Модель", choices=["auto"], value="auto")
                            temperature = gr.Slider(label="Temperature", minimum=0, maximum=1, value=0.7, step=0.1)
                            reasoning_mode = gr.Checkbox(label="🤔 Reasoning", value=False)
                            use_rag = gr.Checkbox(label="📚 Использовать RAG", value=False)
                            gr.Button("🔄 Модели").click(self.get_available_models, outputs=model_dropdown)
                    
                    # Fix: Append transcribed text to avoid overwriting manual input
                    def append_transcription(audio_text, current_text):
                        """Append transcription to existing text instead of replacing."""
                        if not audio_text or audio_text.startswith("["):
                            return current_text  # Error or empty - keep current
                        if current_text:
                            return f"{current_text} {audio_text}"
                        return audio_text
                    
                    audio_input.change(
                        lambda audio: self.transcribe_audio(audio),
                        audio_input,
                        gr.State()
                    ).then(append_transcription, [gr.State(), msg], msg)
                    
                    send_btn.click(self.chat, [msg, chatbot, model_dropdown, temperature, reasoning_mode, use_rag], chatbot).then(lambda: "", outputs=msg)
                    msg.submit(self.chat, [msg, chatbot, model_dropdown, temperature, reasoning_mode, use_rag], chatbot).then(lambda: "", outputs=msg)
                    new_btn.click(self.new_conversation, outputs=[chatbot, status])
                
                # ==================== RAG Tab ====================
                with gr.TabItem("📚 Документы (RAG)"):
                    gr.Markdown("### Загрузка документов для контекста")
                    
                    with gr.Row():
                        file_upload = gr.File(label="Загрузить PDF/DOCX/TXT", file_types=[".pdf", ".docx", ".txt", ".md"])
                        upload_btn = gr.Button("📤 Загрузить", variant="primary")
                    
                    upload_status = gr.Textbox(label="Статус", interactive=False)
                    
                    gr.Markdown("### Загруженные документы")
                    docs_table = gr.Dataframe(headers=["Файл", "Тип", "Chunks", "ID"], label="Документы")
                    
                    with gr.Row():
                        doc_id_input = gr.Textbox(label="ID для удаления", scale=3)
                        delete_doc_btn = gr.Button("🗑️ Удалить", scale=1)
                    
                    upload_btn.click(self.upload_document, file_upload, [upload_status, docs_table])
                    delete_doc_btn.click(self.delete_document, doc_id_input, [upload_status, docs_table])
                    app.load(self.list_documents, outputs=docs_table)
                
                # ==================== AutoGPT Tab ====================
                with gr.TabItem("🤖 Auto-GPT"):
                    gr.Markdown("### Автономное выполнение задач")
                    
                    goal_input = gr.Textbox(label="Цель", placeholder="Опиши задачу для автономного выполнения...")
                    max_steps_slider = gr.Slider(label="Макс. шагов", minimum=5, maximum=50, value=20, step=5)
                    start_autogpt_btn = gr.Button("🚀 Запустить", variant="primary")
                    
                    autogpt_status = gr.Textbox(label="Статус", interactive=False)
                    steps_table = gr.Dataframe(headers=["#", "Действие", "Результат"], label="Шаги")
                    
                    gr.Markdown("### История запусков")
                    runs_table = gr.Dataframe(headers=["ID", "Цель", "Статус", "Шагов"], label="Запуски")
                    
                    start_autogpt_btn.click(self.start_autogpt, [goal_input, max_steps_slider], [autogpt_status, steps_table])
                    app.load(self.list_autogpt_runs, outputs=runs_table)
                
                # ==================== Templates Tab ====================
                with gr.TabItem("📋 Шаблоны"):
                    gr.Markdown("### Сохранённые промпты")
                    
                    templates_table = gr.Dataframe(headers=["Имя", "Категория", "Использований", "ID"], label="Шаблоны")
                    
                    with gr.Row():
                        tpl_id_input = gr.Textbox(label="ID шаблона", scale=2)
                        tpl_vars_input = gr.Textbox(label="Переменные (key=value)", placeholder="text=Привет мир", scale=3)
                        tpl_use_btn = gr.Button("▶️ Использовать", scale=1)
                    
                    tpl_result = gr.Textbox(label="Результат", lines=4, interactive=False)
                    
                    gr.Markdown("---")
                    gr.Markdown("### Добавить шаблон")
                    
                    with gr.Row():
                        new_tpl_name = gr.Textbox(label="Имя", scale=2)
                        new_tpl_category = gr.Textbox(label="Категория", scale=1)
                    new_tpl_prompt = gr.Textbox(label="Промпт (используйте {variable})", lines=3)
                    add_tpl_btn = gr.Button("➕ Добавить шаблон")
                    add_tpl_status = gr.Textbox(label="", interactive=False)
                    
                    tpl_use_btn.click(self.use_template, [tpl_id_input, tpl_vars_input], tpl_result)
                    add_tpl_btn.click(self.add_template, [new_tpl_name, new_tpl_prompt, new_tpl_category], [add_tpl_status, templates_table])
                    app.load(self.list_templates, outputs=templates_table)
                
                # ==================== History Tab ====================
                with gr.TabItem("📜 История"):
                    with gr.Row():
                        search_input = gr.Textbox(label="🔍 Поиск", placeholder="Введите текст...")
                        search_btn = gr.Button("Искать")
                    
                    search_results = gr.Dataframe(headers=["ID", "Роль", "Текст"], label="Результаты")
                    
                    # Logic Fix: Load conversation on click
                    search_results.select(self.load_conversation_from_history, search_results, [chatbot, status])
                    # Switch to chat tab on select
                    search_results.select(lambda: gr.Tabs(selected=0), None, None) 
                    
                    search_btn.click(self.search_history, search_input, search_results)
                
                # ==================== Settings Tab ====================
                with gr.TabItem("⚙️ Настройки"):
                    gr.Markdown("### Персонализация")
                    
                    user_name = gr.Textbox(label="👤 Ваше имя")
                    verbosity = gr.Radio(label="📝 Длина ответов", choices=["brief", "balanced", "detailed"], value="balanced")
                    formality = gr.Radio(label="🎭 Стиль", choices=["formal", "friendly", "casual"], value="friendly")
                    use_emoji = gr.Checkbox(label="😊 Эмодзи", value=True)
                    use_humor = gr.Checkbox(label="😄 Юмор", value=True)
                    
                    save_btn = gr.Button("💾 Сохранить", variant="primary")
                    settings_status = gr.Textbox(label="", interactive=False)
                    
                    async def save_settings(name, verb, form, emoji, humor, danger):
                        if name:
                            await user_profile.set_name(name)
                        await user_profile.update_preference("verbosity", verb)
                        await user_profile.update_preference("formality", form)
                        await user_profile.update_preference("use_emoji", emoji)
                        await user_profile.update_preference("use_humor", humor)
                        # Logic Fix: Save allow_dangerous preference
                        await user_profile.update_preference("allow_dangerous", danger)
                        self.allow_dangerous = danger
                        return "Сохранено!"
                    
                    # P0 Fix: Security Setting
                    allow_dangerous_cb = gr.Checkbox(
                        label="⚠️ Разрешить опасные действия (удаление файлов, системные команды)", 
                        value=self.allow_dangerous,
                        elem_id="danger-check"
                    )
                    
                    save_btn.click(save_settings, [user_name, verbosity, formality, use_emoji, use_humor, allow_dangerous_cb], settings_status)
                
                # ==================== Help Tab ====================
                with gr.TabItem("❓ Помощь"):
                    gr.Markdown("""
## MAX AI Assistant

### Возможности
- 💬 **Чат** — общение с памятью разговоров
- 📚 **RAG** — загрузка документов для контекста
- 🤖 **Auto-GPT** — автономное выполнение задач
- 📋 **Шаблоны** — сохранённые промпты
- 🔍 **Поиск** — по истории и в интернете
- ⚙️ **Персонализация** — стиль ответов под вас

### Примеры
- "Покажи файлы в папке Documents"
- "Найди в интернете новости о AI"
- "Запомни что меня зовут Виталий"
                    """)
            
            app.load(self.initialize)
        
        return app


def create_app() -> gr.Blocks:
    """Create and return the Gradio application."""
    ui = MaxAssistantUI()
    return ui.build_ui()
