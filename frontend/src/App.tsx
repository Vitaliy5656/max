import { useEffect, useRef, useState } from 'react';
import {
  MessageSquare, FileText, Bot, LayoutTemplate, Plus,
  Cpu, History, ChevronDown,
  Menu, X, MessageCircle, ChevronRight, Check, Brain,
  Maximize2, Minimize2
} from 'lucide-react';

// Core components
import { DenseCore } from './components/DenseCore';
import { SynapticStream } from './components/SynapticStream';
import { BrainCanvas } from './components/brain';
import * as api from './api/client';

// Tab components (ARCH-001 to ARCH-006)
import { ChatTab, RagTab, AgentTab, TemplatesTab, HistoryTab } from './components/tabs';
import { ResearchLab } from './components/ResearchLab';

// Custom hooks
import {
  useChat,
  useConversations,
  useModels,
  useMetrics,
  useAgent,
  useUI,
  useKeyboardShortcuts,
  THINKING_MODES
} from './hooks';
import { useBrainMap } from './hooks/useBrainMap';

// ============= Separate Components =============

// UX-004: NavItem with optional badge for activity indicators
const NavItem = ({ icon, label, active, onClick, collapsed, badge }: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  collapsed?: boolean;
  badge?: number | string;
}) => (
  <button
    onClick={onClick}
    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group focus:outline-none focus:ring-2 focus:ring-indigo-500/50 ${active ? 'bg-zinc-800 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
      }`}
    aria-label={collapsed ? label : undefined}
    title={collapsed ? label : undefined}
  >
    <div className={`relative flex items-center justify-center transition-colors ${active ? 'text-indigo-400' : 'group-hover:text-indigo-300'}`}>
      {icon}
      {/* UX-004: Badge indicator */}
      {badge !== undefined && badge !== 0 && (
        <span className="absolute -top-1.5 -right-1.5 min-w-[14px] h-[14px] flex items-center justify-center bg-indigo-500 text-[9px] font-bold text-white rounded-full px-0.5">
          {typeof badge === 'number' && badge > 99 ? '99+' : badge}
        </span>
      )}
    </div>
    {!collapsed && <span className="text-sm truncate flex-1 text-left">{label}</span>}
    {!collapsed && badge !== undefined && badge !== 0 && (
      <span className="bg-indigo-500/20 text-indigo-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
        {typeof badge === 'number' && badge > 99 ? '99+' : badge}
      </span>
    )}
  </button>
);

// Glass card component for consistent styling
export const GlassCard = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
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
  const brainMap = useBrainMap();  // Brain Map hook
  const agent = useAgent({
    onLog: ui.addLog,
    onMetricsRefresh: metrics.loadMetrics
  });
  const chat = useChat({
    onLog: ui.addLog,
    onMetricsRefresh: metrics.loadMetrics
  });

  // UX-001: Global keyboard shortcuts for tab navigation (Ctrl+1-6, Escape)
  useKeyboardShortcuts({
    onTabChange: (tab) => ui.setActiveTab(tab),
    onEscape: () => setDeleteModal({ isOpen: false, docId: '', docName: '' }),
  });

  // Additional local state not in hooks
  const [documents, setDocuments] = useState<api.Document[]>([]);
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; docId: string; docName: string }>({ isOpen: false, docId: '', docName: '' });
  const [isUploading, setIsUploading] = useState(false);
  const [templates, setTemplates] = useState<api.Template[]>([]);
  const [tplCategory, setTplCategory] = useState('All');
  // UX-011: feedbackSent with localStorage persistence
  const [feedbackSent, setFeedbackSent] = useState<Record<number, 'up' | 'down' | null>>(() => {
    try {
      const stored = localStorage.getItem('feedback_sent');
      return stored ? JSON.parse(stored) : {};
    } catch { return {}; }
  });

  // UX-011: Sync feedbackSent to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('feedback_sent', JSON.stringify(feedbackSent));
    } catch (e) {
      console.error('Failed to persist feedback:', e);
    }
  }, [feedbackSent]);


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

        // FIX-011: Use Promise.allSettled for resilient loading
        const [docsResult, tplsResult] = await Promise.allSettled([
          api.getDocuments(),
          api.getTemplates(),
        ]);

        if (docsResult.status === 'fulfilled') setDocuments(docsResult.value);
        if (tplsResult.status === 'fulfilled') setTemplates(tplsResult.value);

        // FIX-011: Continue loading even if some fail
        await Promise.allSettled([
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

  // FIX: handleRegenerate now auto-sends the regeneration request
  async function handleRegenerate(messageId: number) {
    const idx = chat.messages.findIndex(m => m.id === messageId);
    if (idx > 0 && chat.messages[idx - 1].role === 'user') {
      const userContent = chat.messages[idx - 1].content;
      // Remove the assistant message first
      chat.setMessages(prev => prev.filter(m => m.id !== messageId));
      // Set input and immediately trigger send
      chat.setInput(userContent);
      ui.addLog('Регенерация ответа...', 'info');
      // Use setTimeout to ensure state updates before sending
      setTimeout(() => {
        handleSendMessage();
      }, 0);
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
    <div className="relative flex h-screen w-full overflow-hidden bg-[#09090b] text-zinc-100 font-sans selection:bg-indigo-500/30">

      {/* Layer 0: Brain Map Background (always rendered) */}
      <BrainCanvas
        points={brainMap.points}
        connections={brainMap.connections}
        isLoading={brainMap.isLoading}
        isInteractive={ui.brainFullscreen}  // Interactive in fullscreen mode
        showConnections={true}
      />

      {/* Brain Fullscreen Mode Overlay */}
      {ui.brainFullscreen && (
        <div className="fixed inset-0 z-50 flex flex-col">
          {/* Back button */}
          <div className="absolute top-4 right-4 z-50">
            <button
              onClick={() => ui.setBrainFullscreen(false)}
              className="flex items-center gap-2 px-4 py-2 bg-zinc-900/80 backdrop-blur-md border border-white/10 rounded-xl text-white hover:bg-zinc-800 transition-all shadow-lg"
            >
              <Minimize2 size={18} />
              <span>Назад к чату</span>
            </button>
          </div>

          {/* Brain Stats */}
          <div className="absolute bottom-4 left-4 z-50 bg-zinc-900/80 backdrop-blur-md border border-white/10 rounded-xl p-4">
            <div className="text-sm text-zinc-400">Точек знаний: <span className="text-indigo-400 font-bold">{brainMap.points.length}</span></div>
            <div className="text-sm text-zinc-400">Связей: <span className="text-purple-400 font-bold">{brainMap.connections.length}</span></div>
            <div className="text-xs text-zinc-600 mt-1">Используй мышь для вращения</div>
          </div>
        </div>
      )}

      {/* Brain Fullscreen Toggle Button (floating) */}
      {!ui.brainFullscreen && (
        <button
          onClick={() => ui.setBrainFullscreen(true)}
          className="fixed bottom-4 right-4 z-40 flex items-center gap-2 px-3 py-2 bg-indigo-600/80 backdrop-blur-md border border-indigo-500/30 rounded-xl text-white hover:bg-indigo-500 transition-all shadow-lg group"
          title="Полноэкранный режим мозга"
        >
          <Brain size={18} className="group-hover:animate-pulse" />
          <Maximize2 size={16} />
        </button>
      )}

      {/* Mobile Overlay */}
      {ui.isMobile && ui.sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30" onClick={() => ui.setSidebarOpen(false)} />
      )}

      {/* Sidebar - Layer 2 with frosted glass (hidden in brain fullscreen) */}
      {!ui.brainFullscreen && (
        <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        ${ui.sidebarOpen ? 'w-80 translate-x-0' : 'w-20 -translate-x-full lg:translate-x-0'} 
        bg-[#09090b]/80 backdrop-blur-xl border-r border-white/5 flex flex-col transition-all duration-500
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

            {/* UX-014: Show more conversations (10 instead of 5), with scrolling */}
            <div className="space-y-0.5 max-h-64 overflow-y-auto">
              {conversations.conversations.slice(0, 10).map(conv => (
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
              <NavItem icon={<Brain size={18} />} label="Research Lab" active={ui.activeTab === 'research'} onClick={() => ui.setActiveTab('research')} collapsed={!ui.sidebarOpen} />
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
      )}

      {/* Main Content - Layer 1 with frosted glass (hidden in brain fullscreen) */}
      {!ui.brainFullscreen && (
        <main className="flex-1 flex flex-col relative overflow-hidden bg-black/30 backdrop-blur-md">
          {/* Ambient Background (subtle, behind frosted glass) */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,_rgba(79,70,229,0.05),_transparent_40%)] pointer-events-none" />
          <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-indigo-600/3 blur-[120px] rounded-full pointer-events-none" />

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
                  {ui.activeTab === 'research' && 'Research Lab'}
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

                {/* Provider Toggle (Phase 8) */}
                <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1 border border-white/5">
                  <button
                    onClick={() => { models.updateProvider('lmstudio'); ui.addLog('Провайдер: Локальный', 'info'); }}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${models.provider === 'lmstudio'
                      ? 'bg-emerald-500/20 text-emerald-400 shadow-md'
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
                      }`}
                    title="Локальная модель (LM Studio)"
                  >
                    <span>💻</span>
                    <span className="hidden lg:inline">Локальная</span>
                  </button>
                  <button
                    onClick={() => { models.updateProvider('gemini'); ui.addLog('Провайдер: Gemini Cloud', 'info'); }}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${models.provider === 'gemini'
                      ? 'bg-blue-500/20 text-blue-400 shadow-md'
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
                      }`}
                    title="Облачная модель (Gemini Flash)"
                  >
                    <span>☁️</span>
                    <span className="hidden lg:inline">Облако</span>
                  </button>
                </div>
              </div>
            )}
          </header>

          {/* Chat Tab */}
          {ui.activeTab === 'chat' && (
            <ChatTab
              messages={chat.messages}
              input={chat.input}
              setInput={chat.setInput}
              isGenerating={chat.isGenerating}
              isConnecting={chat.isConnecting}
              isThinking={chat.isThinking}
              thinkingStartTime={chat.thinkingStartTime}
              thinkContent={chat.thinkContent}
              thinkExpanded={chat.thinkExpanded}
              toggleThinkExpanded={chat.toggleThinkExpanded}
              thinkingSteps={chat.thinkingSteps}
              lastConfidence={chat.lastConfidence}
              loadingModel={chat.loadingModel}
              queueStatus={chat.queueStatus}
              feedbackSent={feedbackSent}
              onSendMessage={handleSendMessage}
              onStopGeneration={chat.stopGeneration}
              onCopy={handleCopy}
              onRegenerate={handleRegenerate}
              onFeedback={handleFeedback}
            />
          )}

          {/* RAG Tab */}
          {ui.activeTab === 'rag' && (
            <RagTab
              documents={documents}
              isUploading={isUploading}
              deleteModal={deleteModal}
              setDeleteModal={setDeleteModal}
              onUploadDocument={handleUploadDocument}
              onDeleteDocument={handleDeleteDocument}
            />
          )}

          {/* Research Lab Tab */}
          {ui.activeTab === 'research' && (
            <div className="flex-1 overflow-hidden animate-tab-in">
              <ResearchLab />
            </div>
          )}

          {/* Auto-GPT Tab */}
          {ui.activeTab === 'autogpt' && (
            <AgentTab agent={agent} />
          )}

          {/* Templates Tab */}
          {ui.activeTab === 'templates' && (
            <TemplatesTab
              templates={templates}
              filteredTemplates={filteredTemplates}
              tplCategory={tplCategory}
              setTplCategory={setTplCategory}
              onUseTemplate={handleUseTemplate}
            />
          )}

          {/* History Tab */}
          {ui.activeTab === 'history' && (
            <HistoryTab
              conversations={conversations.conversations}
              onSelectConversation={conversations.selectConversation}
              onSwitchToChat={() => ui.setActiveTab('chat')}
            />
          )}
        </main>
      )}
    </div>
  );
}
