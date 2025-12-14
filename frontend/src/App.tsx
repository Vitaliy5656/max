import { useEffect, useRef, useState } from 'react';
import {
  MessageSquare, FileText, Bot, LayoutTemplate, Plus,
  Cpu, Trash2, Play, CheckCircle2, History, ChevronDown, RotateCw,
  Menu, X, MessageCircle, ChevronRight, Check, AlertTriangle, Loader2
} from 'lucide-react';

// Core components
import { DenseCore } from './components/DenseCore';
import { SynapticStream } from './components/SynapticStream';
import * as api from './api/client';

// Atomic components
import { InputArea } from './components/InputArea';
import { ThinkingPanel } from './components/ThinkingPanel';
import { MessageBubble } from './components/MessageBubble';

// Custom hooks
import {
  useChat,
  useConversations,
  useModels,
  useMetrics,
  useAgent,
  useUI,
  THINKING_MODES
} from './hooks';

// ============= Separate Components =============

const NavItem = ({ icon, label, active, onClick, collapsed }: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  collapsed?: boolean
}) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-indigo-500/50 ${active ? 'bg-zinc-800 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
      }`}
    aria-label={collapsed ? label : undefined}
    title={collapsed ? label : undefined}
  >
    <div className={`flex items-center justify-center transition-colors ${active ? 'text-indigo-400' : 'group-hover:text-indigo-300'}`}>
      {icon}
    </div>
    {!collapsed && <span className="text-sm truncate flex-1 text-left">{label}</span>}
  </button>
);

const GlassCard = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-sm ${className}`}>
    {children}
  </div>
);

// ============= Main App Component =============

export default function App() {
  // Initialize hooks
  const ui = useUI();
  const metrics = useMetrics();
  const models = useModels();
  const conversations = useConversations();
  const agent = useAgent({
    onLog: ui.addLog,
    onMetricsRefresh: metrics.loadMetrics
  });
  const chat = useChat({
    onLog: ui.addLog,
    onMetricsRefresh: metrics.loadMetrics
  });

  // Additional local state not in hooks
  const [documents, setDocuments] = useState<api.Document[]>([]);
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; docId: string; docName: string }>({ isOpen: false, docId: '', docName: '' });
  const [isUploading, setIsUploading] = useState(false);
  const [templates, setTemplates] = useState<api.Template[]>([]);
  const [tplCategory, setTplCategory] = useState('All');
  const [feedbackSent, setFeedbackSent] = useState<Record<number, 'up' | 'down' | null>>({});
  // eslint-disable-next-line @typescript-eslint/no-unused-vars


  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  // ============= Effects =============

  // Load initial data
  useEffect(() => {
    async function loadInitialData() {
      try {
        await api.checkHealth();
        ui.addLog('Подключено к MAX AI', 'growth');

        const [docs, tpls] = await Promise.all([
          api.getDocuments(),
          api.getTemplates(),
        ]);

        setDocuments(docs);
        setTemplates(tpls);

        await Promise.all([
          conversations.loadConversations(),
          models.loadModels(),
          models.loadModelSelectionMode(),
          metrics.loadMetrics(),
        ]);
      } catch (error) {
        ui.addLog('Ошибка подключения к API', 'error');
        console.error('Failed to load initial data:', error);
      }
    }

    loadInitialData();
    const interval = setInterval(metrics.loadMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  // Load messages when conversation changes
  useEffect(() => {
    if (conversations.conversationId) {
      chat.loadMessages(conversations.conversationId);
    }
  }, [conversations.conversationId]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages, chat.isGenerating]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        models.setModelDropdownOpen(false);
      }
    };
    if (models.modelDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [models.modelDropdownOpen]);



  // ============= Handlers =============

  async function handleSendMessage() {
    await chat.sendMessage(
      conversations.conversationId,
      models.selectedModel,
      models.thinkingMode,
      (id) => conversations.setConversationId(id)
    );
  }

  async function handleNewConversation() {
    await conversations.createConversation();
    chat.clearMessages();
    ui.addLog('Новый разговор создан', 'info');

    // Refresh conversations list
    conversations.loadConversations();
  }

  async function handleFeedback(messageId: number, rating: number) {
    setFeedbackSent(prev => ({ ...prev, [messageId]: rating > 0 ? 'up' : 'down' }));
    await api.submitFeedback(messageId, rating);
    if (rating > 0) {
      ui.addLog('Эмпатия повышена: резонанс', 'empathy');
    } else {
      ui.addLog('Feedback отправлен', 'info');
    }
    metrics.loadMetrics();
  }

  async function handleRegenerate(messageId: number) {
    const idx = chat.messages.findIndex(m => m.id === messageId);
    if (idx > 0 && chat.messages[idx - 1].role === 'user') {
      chat.setInput(chat.messages[idx - 1].content);
      chat.setMessages(prev => prev.filter(m => m.id !== messageId));
      ui.addLog('Regenerating response...', 'info');
    }
  }

  function handleCopy(content: string) {
    navigator.clipboard.writeText(content);
    ui.addLog('Текст скопирован в буфер', 'info');
  }

  // Document handlers
  async function handleUploadDocument(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || isUploading) return;

    setIsUploading(true);
    try {
      await api.uploadDocument(file);
      ui.addLog(`Файл "${file.name}" загружен`, 'growth');
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (error) {
      ui.addLog('Ошибка загрузки файла', 'error');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  }

  async function handleDeleteDocument() {
    await api.deleteDocument(deleteModal.docId);
    ui.addLog(`Файл "${deleteModal.docName}" удален`, 'info');
    setDeleteModal({ isOpen: false, docId: '', docName: '' });
    const docs = await api.getDocuments();
    setDocuments(docs);
  }

  // Template handler
  function handleUseTemplate(tpl: api.Template) {
    ui.setActiveTab('chat');
    chat.setInput(tpl.content);
    ui.addLog(`Применен шаблон: ${tpl.name}`, 'info');
  }

  const filteredTemplates = tplCategory === 'All'
    ? templates
    : templates.filter(t => t.category === tplCategory);

  // ============= Render =============

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#09090b] text-zinc-100 font-sans selection:bg-indigo-500/30">

      {/* Mobile Overlay */}
      {ui.isMobile && ui.sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30" onClick={() => ui.setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        ${ui.sidebarOpen ? 'w-80 translate-x-0' : 'w-20 -translate-x-full lg:translate-x-0'} 
        bg-[#09090b] border-r border-white/5 flex flex-col transition-all duration-500
      `}>
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/5 shrink-0">
          <div className="flex items-center">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-[0_0_15px_rgba(79,70,229,0.4)]">
              <Cpu size={20} className="text-white" />
            </div>
            {ui.sidebarOpen && <span className="ml-3 font-bold text-xl tracking-tight text-white">MAX <span className="text-zinc-500 font-normal">AI</span></span>}
          </div>
          {ui.sidebarOpen && <button onClick={() => ui.setSidebarOpen(false)} className="lg:hidden text-zinc-500 hover:text-white"><X size={20} /></button>}
        </div>

        {/* Navigation */}
        <div className="flex-1 flex flex-col overflow-y-auto py-4 px-3 gap-1">
          <NavItem icon={<Plus size={18} />} label="Новый чат" active={false} onClick={handleNewConversation} collapsed={!ui.sidebarOpen} />
          <NavItem icon={<MessageSquare size={18} />} label="Текущий чат" active={ui.activeTab === 'chat'} onClick={() => ui.setActiveTab('chat')} collapsed={!ui.sidebarOpen} />

          {ui.sidebarOpen && conversations.conversations.length > 0 && (
            <div className="mt-6 mb-2 px-2 flex items-center justify-between">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider">Недавние диалоги</span>
              <span className="text-[10px] text-zinc-700 bg-zinc-900 px-1.5 py-0.5 rounded-md border border-white/5">{conversations.conversations.length}</span>
            </div>
          )}

          <div className="space-y-0.5">
            {conversations.conversations.slice(0, 5).map(conv => (
              <button
                key={conv.id}
                onClick={() => { conversations.selectConversation(conv.id); ui.setActiveTab('chat'); }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group text-left hover:bg-zinc-900/50"
              >
                <MessageCircle size={16} className="text-zinc-500 group-hover:text-zinc-300" />
                {ui.sidebarOpen && (
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-zinc-400 group-hover:text-zinc-200 truncate">{conv.title}</div>
                    <div className="text-[10px] text-zinc-600 truncate">{conv.message_count} сообщ.</div>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tools */}
        <div className="shrink-0 bg-[#09090b] border-t border-white/5 flex flex-col">
          <div className="px-3 py-4 space-y-1">
            {ui.sidebarOpen && <div className="px-2 mb-2 text-[10px] font-bold text-zinc-600 uppercase tracking-wider">Инструменты</div>}
            <NavItem icon={<FileText size={18} />} label="База знаний (RAG)" active={ui.activeTab === 'rag'} onClick={() => ui.setActiveTab('rag')} collapsed={!ui.sidebarOpen} />
            <NavItem icon={<Bot size={18} />} label="Авто-агент" active={ui.activeTab === 'autogpt'} onClick={() => ui.setActiveTab('autogpt')} collapsed={!ui.sidebarOpen} />
            <NavItem icon={<LayoutTemplate size={18} />} label="Шаблоны" active={ui.activeTab === 'templates'} onClick={() => ui.setActiveTab('templates')} collapsed={!ui.sidebarOpen} />
            <NavItem icon={<History size={18} />} label="Архив" active={ui.activeTab === 'history'} onClick={() => ui.setActiveTab('history')} collapsed={!ui.sidebarOpen} />
          </div>

          {!ui.sidebarOpen && (
            <button onClick={() => ui.setSidebarOpen(true)} className="w-full flex items-center justify-center p-4 text-zinc-600 hover:text-white border-t border-white/5">
              <ChevronRight size={18} />
            </button>
          )}

          {/* The Living Core */}
          {ui.sidebarOpen && (
            <div className="p-4 pt-2 border-t border-white/5 flex flex-col items-center">
              <SynapticStream logs={ui.systemLogs} />
              <DenseCore intelligence={metrics.intelligence} empathy={metrics.empathy} />
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative overflow-hidden bg-[#09090b]">
        {/* Ambient Background */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_rgba(79,70,229,0.08),_transparent_40%)] pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-indigo-600/5 blur-[120px] rounded-full pointer-events-none" />

        {/* Header */}
        <header className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-white/5 bg-[#09090b]/80 backdrop-blur-xl z-10 sticky top-0">
          <div className="flex items-center gap-3">
            <button onClick={ui.toggleSidebar} className="lg:hidden p-2 -ml-2 text-zinc-400 hover:text-white rounded-lg">
              <Menu size={20} />
            </button>

            {ui.activeTab === 'chat' ? (
              <div className="relative" ref={modelDropdownRef}>
                <button
                  onClick={() => models.setModelDropdownOpen(!models.modelDropdownOpen)}
                  className="flex items-center gap-2 cursor-pointer px-2 py-1.5 rounded-lg hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                >
                  <span className="text-lg font-semibold text-white/90">MAX AI</span>
                  <span className="text-zinc-600">/</span>
                  <div className="flex items-center gap-2 text-sm text-zinc-300">
                    <span>{models.getModelDisplayName(models.selectedModel)}</span>
                    <ChevronDown size={14} className={`text-zinc-500 transition-transform ${models.modelDropdownOpen ? 'rotate-180' : ''}`} />
                  </div>
                </button>
                {models.modelDropdownOpen && (
                  <div className="absolute top-full left-0 mt-2 w-48 bg-zinc-900 border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
                    {models.availableModels.map(model => (
                      <button
                        key={model}
                        onClick={() => { models.setSelectedModel(model); models.setModelDropdownOpen(false); ui.addLog(`Модель: ${model}`, 'info'); }}
                        className={`w-full px-4 py-2.5 text-left text-sm hover:bg-white/5 transition-colors flex items-center justify-between
                          ${models.selectedModel === model ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-300'}`}
                      >
                        {models.getModelDisplayName(model)}
                        {models.selectedModel === model && <Check size={14} />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <h2 className="text-lg font-semibold text-white/90">
                {ui.activeTab === 'rag' && 'База Знаний'}
                {ui.activeTab === 'autogpt' && 'Автономный Агент'}
                {ui.activeTab === 'templates' && 'Галерея Шаблонов'}
                {ui.activeTab === 'history' && 'Архив Событий'}
              </h2>
            )}
          </div>

          {/* Thinking Mode Selector */}
          {ui.activeTab === 'chat' && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1">
                {THINKING_MODES.map(mode => (
                  <button
                    key={mode.id}
                    onClick={() => { models.setThinkingMode(mode.id); ui.addLog(`Режим: ${mode.label}`, 'info'); }}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${models.thinkingMode === mode.id
                      ? `${mode.bgActive} ${mode.color} shadow-md`
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
                      }`}
                    title={mode.label}
                  >
                    <span>{mode.icon}</span>
                    <span className="hidden md:inline ml-1">{mode.label}</span>
                  </button>
                ))}
              </div>

              {/* Model Selection Mode Toggle */}
              <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1 border border-white/5">
                <button
                  onClick={() => models.updateModelSelectionMode('manual')}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${models.modelSelectionMode === 'manual'
                    ? 'bg-emerald-500/20 text-emerald-400 shadow-md'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
                    }`}
                >
                  <span>🎯</span>
                  <span className="hidden lg:inline">Ручной</span>
                </button>
                <button
                  onClick={() => models.updateModelSelectionMode('auto')}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${models.modelSelectionMode === 'auto'
                    ? 'bg-purple-500/20 text-purple-400 shadow-md'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
                    }`}
                >
                  <span>🧠</span>
                  <span className="hidden lg:inline">Авто</span>
                </button>
              </div>
            </div>
          )}
        </header>

        {/* Chat Tab */}
        {ui.activeTab === 'chat' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-4">
              {chat.messages.map(message => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  feedbackSent={feedbackSent}
                  onCopy={handleCopy}
                  onRegenerate={handleRegenerate}
                  onFeedback={handleFeedback}
                />
              ))}

              {/* Thinking Panel */}
              <ThinkingPanel
                isThinking={chat.isThinking}
                thinkingStartTime={chat.thinkingStartTime}
                thinkContent={chat.thinkContent}
                thinkExpanded={chat.thinkExpanded}
                onToggleExpand={chat.toggleThinkExpanded}
                lastConfidence={chat.lastConfidence}
                loadingModel={chat.loadingModel}
                isGenerating={chat.isGenerating}
                queueStatus={chat.queueStatus}
              />

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <InputArea
              value={chat.input}
              onChange={chat.setInput}
              onSend={handleSendMessage}
              onStop={chat.stopGeneration}
              isGenerating={chat.isGenerating}
            />
          </div>
        )}

        {/* RAG Tab */}
        {ui.activeTab === 'rag' && (
          <div className="flex-1 overflow-y-auto p-6">
            <GlassCard className="p-6">
              <h3 className="text-lg font-semibold mb-4">📚 База Знаний (RAG)</h3>

              {/* Upload */}
              <div className="mb-6">
                <label className="flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600/20 border border-indigo-500/30 rounded-xl cursor-pointer hover:bg-indigo-600/30 transition-colors">
                  <Plus size={18} />
                  <span>{isUploading ? 'Загрузка...' : 'Загрузить документ'}</span>
                  <input type="file" className="hidden" onChange={handleUploadDocument} accept=".pdf,.docx,.txt,.md" />
                </label>
              </div>

              {/* Documents List */}
              <div className="space-y-2">
                {documents.length === 0 ? (
                  <p className="text-zinc-500 text-center py-8">Нет загруженных документов</p>
                ) : (
                  documents.map(doc => (
                    <div key={doc.id} className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <FileText size={18} className="text-indigo-400" />
                        <span className="text-sm">{doc.name}</span>
                      </div>
                      <button
                        onClick={() => setDeleteModal({ isOpen: true, docId: doc.id, docName: doc.name })}
                        className="p-2 text-zinc-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </GlassCard>

            {/* Delete Modal */}
            {deleteModal.isOpen && (
              <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                <GlassCard className="p-6 max-w-sm">
                  <h3 className="text-lg font-semibold mb-4">Удалить документ?</h3>
                  <p className="text-zinc-400 mb-6">"{deleteModal.docName}" будет удален безвозвратно.</p>
                  <div className="flex gap-3">
                    <button onClick={() => setDeleteModal({ isOpen: false, docId: '', docName: '' })} className="flex-1 px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700">Отмена</button>
                    <button onClick={handleDeleteDocument} className="flex-1 px-4 py-2 bg-red-600 rounded-lg hover:bg-red-500">Удалить</button>
                  </div>
                </GlassCard>
              </div>
            )}
          </div>
        )}

        {/* Auto-GPT Tab */}
        {ui.activeTab === 'autogpt' && (
          <div className="flex-1 overflow-y-auto p-6">
            <GlassCard className="p-6">
              <h3 className="text-lg font-semibold mb-4">🤖 Автономный Агент</h3>

              {/* Goal Input */}
              <div className="mb-6">
                <textarea
                  value={agent.agentGoal}
                  onChange={(e) => agent.setAgentGoal(e.target.value)}
                  placeholder="Опишите цель для агента..."
                  className="w-full bg-zinc-800/50 border border-white/10 rounded-xl p-4 text-sm resize-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50"
                  rows={3}
                />
              </div>

              {/* Start/Stop Button */}
              <button
                onClick={agent.requestAgent}
                disabled={agent.agentRunning || !agent.agentGoal.trim()}
                className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-colors ${agent.agentRunning
                  ? 'bg-amber-600/20 text-amber-400 cursor-wait'
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                  }`}
              >
                {agent.agentRunning ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Выполняется...
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    Запустить агента
                  </>
                )}
              </button>

              {/* Steps */}
              {agent.agentSteps.length > 0 && (
                <div className="mt-6 space-y-2">
                  <h4 className="text-sm font-medium text-zinc-400">Шаги:</h4>
                  {agent.agentSteps.map((step, idx) => (
                    <div key={step.id || idx} className="flex items-start gap-3 p-3 bg-zinc-800/30 rounded-lg">
                      {step.status === 'completed' ? (
                        <CheckCircle2 size={18} className="text-emerald-400 mt-0.5" />
                      ) : step.status === 'failed' ? (
                        <AlertTriangle size={18} className="text-red-400 mt-0.5" />
                      ) : (
                        <Loader2 size={18} className="text-indigo-400 animate-spin mt-0.5" />
                      )}
                      <div>
                        <p className="text-sm font-medium">{step.title || step.action}</p>
                        {step.desc && <p className="text-xs text-zinc-500 mt-1">{step.desc}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Retry button */}
              {agent.agentFailed && !agent.agentRunning && (
                <button
                  onClick={agent.confirmAgent}
                  className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-2 bg-amber-600/20 text-amber-400 border border-amber-500/30 rounded-xl hover:bg-amber-600/30"
                >
                  <RotateCw size={16} />
                  Повторить
                </button>
              )}
            </GlassCard>

            {/* Confirm Modal */}
            {agent.agentConfirmModal && (
              <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                <GlassCard className="p-6 max-w-sm">
                  <h3 className="text-lg font-semibold mb-4">⚠️ Запустить агента?</h3>
                  <p className="text-zinc-400 mb-6">Агент будет выполнять действия автономно. Убедитесь, что цель сформулирована правильно.</p>
                  <div className="flex gap-3">
                    <button onClick={agent.cancelAgent} className="flex-1 px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700">Отмена</button>
                    <button onClick={agent.confirmAgent} className="flex-1 px-4 py-2 bg-indigo-600 rounded-lg hover:bg-indigo-500">Запустить</button>
                  </div>
                </GlassCard>
              </div>
            )}
          </div>
        )}

        {/* Templates Tab */}
        {ui.activeTab === 'templates' && (
          <div className="flex-1 overflow-y-auto p-6">
            <GlassCard className="p-6">
              <h3 className="text-lg font-semibold mb-4">📋 Шаблоны промптов</h3>

              {/* Category Filter */}
              <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                {['All', ...new Set(templates.map(t => t.category))].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setTplCategory(cat)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${tplCategory === cat
                      ? 'bg-indigo-600 text-white'
                      : 'bg-zinc-800 text-zinc-400 hover:text-white'
                      }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Templates Grid */}
              <div className="grid gap-3">
                {filteredTemplates.length === 0 ? (
                  <p className="text-zinc-500 text-center py-8">Нет шаблонов</p>
                ) : (
                  filteredTemplates.map(tpl => (
                    <button
                      key={tpl.id}
                      onClick={() => handleUseTemplate(tpl)}
                      className="text-left p-4 bg-zinc-800/50 hover:bg-zinc-800 rounded-xl transition-colors"
                    >
                      <h4 className="font-medium mb-1">{tpl.name}</h4>
                      <p className="text-xs text-zinc-500 line-clamp-2">{tpl.content}</p>
                    </button>
                  ))
                )}
              </div>
            </GlassCard>
          </div>
        )}

        {/* History Tab */}
        {ui.activeTab === 'history' && (
          <div className="flex-1 overflow-y-auto p-6">
            <GlassCard className="p-6">
              <h3 className="text-lg font-semibold mb-4">📜 Архив разговоров</h3>
              <div className="space-y-2">
                {conversations.conversations.length === 0 ? (
                  <p className="text-zinc-500 text-center py-8">Нет сохраненных разговоров</p>
                ) : (
                  conversations.conversations.map(conv => (
                    <button
                      key={conv.id}
                      onClick={() => { conversations.selectConversation(conv.id); ui.setActiveTab('chat'); }}
                      className="w-full text-left p-4 bg-zinc-800/50 hover:bg-zinc-800 rounded-xl transition-colors"
                    >
                      <h4 className="font-medium mb-1">{conv.title}</h4>
                      <p className="text-xs text-zinc-500">{conv.message_count} сообщений</p>
                    </button>
                  ))
                )}
              </div>
            </GlassCard>
          </div>
        )}
      </main>
    </div>
  );
}
