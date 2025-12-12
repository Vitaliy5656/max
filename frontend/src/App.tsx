import { useState, useEffect, useRef } from 'react';
import {
  MessageSquare, FileText, Bot, LayoutTemplate, Search, Plus, Send,
  Cpu, Trash2, Play, CheckCircle2, History, ChevronDown, Copy, RotateCw,
  ThumbsUp, ThumbsDown, Sun, Moon, Menu, X, MessageCircle,
  Code, Briefcase, PenTool, ArrowRight, ChevronRight, Check, Loader2, AlertTriangle
} from 'lucide-react';

import { DenseCore } from './components/DenseCore';
import { SynapticStream } from './components/SynapticStream';
import type { LogEntry } from './components/SynapticStream';
import * as api from './api/client';

// ============= Types =============

interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  model?: string;
}

// ============= Separate Components (Performance Fix) =============

const NavItem = ({ icon, label, active, onClick, collapsed }: { icon: React.ReactNode; label: string; active: boolean; onClick: () => void; collapsed?: boolean }) => (
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

const TextAreaContainer = ({ children, isGenerating }: { children: React.ReactNode; isGenerating: boolean }) => (
  <div className={`relative bg-zinc-900/90 backdrop-blur-xl border transition-all duration-300 rounded-[2rem] shadow-2xl overflow-hidden ${isGenerating ? 'border-indigo-500/30 ring-1 ring-indigo-500/10' : 'border-white/10 hover:border-white/20'
    }`}
    style={{ paddingBottom: 'env(safe-area-inset-bottom)' }} // Handle iOS Home Bar
  >
    {children}
  </div>
);

const IconButton = ({ icon, tooltip, onClick, label }: { icon: React.ReactNode; tooltip?: string; onClick?: () => void; label?: string }) => (
  <div className="group relative flex items-center justify-center">
    <button
      onClick={onClick}
      className="p-2 rounded-lg transition-all duration-200 active:scale-95 text-zinc-400 hover:text-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
      aria-label={label || tooltip}
    >
      {icon}
    </button>
    {tooltip && (
      <span className="absolute top-10 scale-0 transition-all duration-200 rounded-lg bg-zinc-800 px-3 py-1.5 text-xs font-medium text-white group-hover:scale-100 z-50 whitespace-nowrap border border-zinc-700 shadow-xl pointer-events-none">
        {tooltip}
      </span>
    )}
  </div>
);

const ActionBtn = ({ icon, onClick, label }: { icon: React.ReactNode; onClick?: () => void; label: string }) => (
  <button
    onClick={onClick}
    className="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 rounded-md transition-colors active:scale-90 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
    aria-label={label}
    title={label}
  >
    {icon}
  </button>
);

// ============= App =============

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState<'chat' | 'rag' | 'autogpt' | 'templates' | 'history'>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  // Chat State
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, role: 'system', content: 'Привет! Я MAX. Мои нейронные связи готовы к работе. Чем займемся?', timestamp: '10:00', model: 'System' }
  ]);
  const [inputVal, setInputVal] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingStartTime, setThinkingStartTime] = useState<number>(0);
  const [thinkContent, setThinkContent] = useState<string>('');  // Think content for collapsible
  const [thinkExpanded, setThinkExpanded] = useState(false);     // Think block expanded
  const [lastConfidence, setLastConfidence] = useState<{ score: number; level: string } | null>(null);
  const [loadingModel, setLoadingModel] = useState<string | null>(null);  // Issue #6: Model loading state
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<api.Conversation[]>([]);
  const [selectedModel, setSelectedModel] = useState('auto');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState([
    'auto',
    'gpt-oss-20b',
    'deepseek-r1-distill-llama-8b',
    'ministral-3-14b-reasoning',
    'mistral-community-pixtral-12b',
  ]);

  // Human-readable model names for UI display
  const modelNames: Record<string, string> = {
    'auto': '🧠 Auto (Smart)',
    'gpt-oss-20b': '🔥 GPT-OSS 20B',
    'deepseek-r1-distill-llama-8b': '🚀 DeepSeek R1 8B',
    'ministral-3-14b-reasoning': '🤔 Ministral 14B Reasoning',
    'mistral-community-pixtral-12b': '👁️ Pixtral 12B Vision',
  };

  // Thinking Mode State
  const [thinkingMode, setThinkingMode] = useState<'fast' | 'standard' | 'deep'>('standard');
  // Future: Image upload will set hasImage for vision mode (feature in backlog)

  // Thinking Modes Configuration
  const thinkingModes = [
    { id: 'fast' as const, icon: '⚡', label: 'Быстро', color: 'text-yellow-400', bgActive: 'bg-yellow-500/20' },
    { id: 'standard' as const, icon: '🧠', label: 'Обычно', color: 'text-indigo-400', bgActive: 'bg-indigo-500/20' },
    { id: 'deep' as const, icon: '🤔', label: 'Глубоко', color: 'text-purple-400', bgActive: 'bg-purple-500/20' },
  ];

  const [feedbackSent, setFeedbackSent] = useState<Record<number, 'up' | 'down' | null>>({});
  const [searchQuery, setSearchQuery] = useState('');
  // P3 Fix: Dark mode state (app is dark by default)
  const [darkMode, setDarkMode] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);  // P2 fix: ref for outside click

  // RAG State
  const [documents, setDocuments] = useState<api.Document[]>([]);
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; docId: string; docName: string }>({ isOpen: false, docId: '', docName: '' });
  const [isUploading, setIsUploading] = useState(false);

  // Auto-GPT State
  const [agentGoal, setAgentGoal] = useState('');
  const [agentRunning, setAgentRunning] = useState(false);
  const [agentSteps, setAgentSteps] = useState<api.AgentStep[]>([]);
  const [agentConfirmModal, setAgentConfirmModal] = useState(false);
  // P3 Fix: Track failed state to enable Retry (STATE BUG #1)
  const [agentFailed, setAgentFailed] = useState(false);

  // Templates State
  const [templates, setTemplates] = useState<api.Template[]>([]);
  const [tplCategory, setTplCategory] = useState('All');

  // Metrics State
  const [intelligence, setIntelligence] = useState(30);
  const [empathy, setEmpathy] = useState(30);
  const [systemLogs, setSystemLogs] = useState<LogEntry[]>([]);

  // Backup Status State
  const [backupStatus, setBackupStatus] = useState<'synced' | 'syncing' | 'error' | 'unknown'>('unknown');

  // ============= Effects =============

  // Responsive
  // Effect to load messages when conversationId changes
  useEffect(() => {
    async function loadConversationMessages() {
      if (!conversationId) return;

      try {
        const msgs = await api.getMessages(conversationId);

        if (msgs.length > 0) {
          setMessages(msgs.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            model: m.model_used
          })));
          addLog('История загружена', 'info');
        } else {
          // Empty conversation (newly created) - Show welcome message
          setMessages([
            { id: 1, role: 'system', content: 'Новый разговор начат. Чем могу помочь?', timestamp: typeof formatTime === 'function' ? formatTime() : new Date().toLocaleTimeString(), model: 'System' }
          ]);
        }
      } catch (error) {
        console.error('Failed to load messages:', error);
        addLog('Ошибка загрузки истории', 'error');
      }
    }

    loadConversationMessages();
  }, [conversationId]);

  // Responsive
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      if (mobile) setSidebarOpen(false);
      else setSidebarOpen(true);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // P2 fix: Close model dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false);
      }
    };
    if (modelDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [modelDropdownOpen]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [inputVal]);

  // Load initial data
  useEffect(() => {
    loadInitialData();
    // Poll metrics every 30 seconds
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  // ============= Data Loading =============

  async function loadInitialData() {
    try {
      await api.checkHealth();
      addLog('Подключено к MAX AI', 'growth');

      const [convs, docs, tpls] = await Promise.all([
        api.getConversations(),
        api.getDocuments(),
        api.getTemplates(),
      ]);

      setConversations(convs);
      setDocuments(docs);
      setTemplates(tpls);

      // P1 Fix: Fetch models from API instead of hardcoded list
      try {
        const modelResponse = await api.getModels();
        if (modelResponse.models && modelResponse.models.length > 0) {
          setAvailableModels(['auto', ...modelResponse.models]);
        }
      } catch {
        // Keep defaults if model fetch fails
      }

      await loadMetrics();
    } catch (error) {
      addLog('Ошибка подключения к API', 'error');
      console.error('Failed to load initial data:', error);
    }
  }

  async function loadMetrics() {
    try {
      const metrics = await api.getMetrics();
      setIntelligence(metrics.iq.score);
      setEmpathy(metrics.empathy.score);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
  }

  // Backup status polling
  useEffect(() => {
    async function checkBackupStatus() {
      try {
        const status = await api.getBackupStatus();
        if (status.status === 'complete' && status.cloud_synced) {
          setBackupStatus('synced');
        } else if (status.status === 'backing_up' || status.status === 'in_progress') {
          setBackupStatus('syncing');
        } else if (status.status === 'error') {
          setBackupStatus('error');
        } else {
          setBackupStatus(status.cloud_synced ? 'synced' : 'unknown');
        }
      } catch {
        // API not available, ignore
      }
    }

    checkBackupStatus();
    const interval = setInterval(checkBackupStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // ============= Helpers =============

  function addLog(text: string, type: LogEntry['type'] = 'info') {
    const newLog: LogEntry = {
      id: Date.now(),
      text,
      type,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setSystemLogs(prev => [...prev, newLog]);
  }

  function formatTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // ============= Chat Handlers =============

  const abortControllerRef = useRef<AbortController | null>(null);

  async function handleSendMessage() {
    if (!inputVal.trim() || isGenerating) return;

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: inputVal,
      timestamp: formatTime()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputVal('');
    setIsGenerating(true);

    const assistantId = Date.now() + 1;
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: formatTime(),
      model: selectedModel
    }]);

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    try {
      await api.streamChat(
        userMessage.content,
        conversationId ?? undefined,
        selectedModel,
        0.7,
        true,
        thinkingMode,   // Pass thinking mode
        false,          // hasImage: will be true when image upload implemented
        (token) => {
          // When we receive tokens, thinking is done
          if (isThinking) {
            setIsThinking(false);
          }
          setMessages(prev => prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, content: msg.content + token }
              : msg
          ));
        },
        (data) => {
          setConversationId(data.conversation_id);
          addLog('Ответ сгенерирован', 'growth');
          loadMetrics(); // Refresh metrics after response
        },
        (error) => {
          // Handle streaming errors from backend
          addLog(`Ошибка стрима: ${error}`, 'error');
          setMessages(prev => prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, content: msg.content + `\n\n⚠️ ${error}` }
              : msg
          ));
        },
        // onThinking callback
        (thinkingEvent) => {
          if (thinkingEvent.status === 'start') {
            setIsThinking(true);
            setThinkingStartTime(Date.now());
            setThinkContent('');  // Reset think content
            setThinkExpanded(false);
            addLog('🧠 MAX думает...', 'info');
          } else if (thinkingEvent.status === 'end') {
            setIsThinking(false);
            if (thinkingEvent.think_content) {
              setThinkContent(thinkingEvent.think_content);
            }
            const durationSec = ((thinkingEvent.duration_ms || 0) / 1000).toFixed(1);
            addLog(`🧠 Обдумал за ${durationSec}s`, 'growth');
          }
        },
        // onConfidence callback
        (confidenceEvent) => {
          setLastConfidence({
            score: confidenceEvent.score,
            level: confidenceEvent.level
          });
          const emoji = confidenceEvent.level === 'high' ? '🟢' : confidenceEvent.level === 'medium' ? '🟡' : '🔴';
          addLog(`${emoji} Уверенность: ${Math.round(confidenceEvent.score * 100)}%`, 'growth');
        },
        // Issue #6: onLoading callback for model switch
        (loadingEvent) => {
          if (loadingEvent.model) {
            setLoadingModel(loadingEvent.model);
            addLog(`🔄 Загрузка модели: ${loadingEvent.model}...`, 'info');
          }
        },
        abortControllerRef.current.signal
      );
    } catch (error: any) {
      if (error.name === 'AbortError') {
        addLog('Генерация остановлена пользователем', 'info');
        setMessages(prev => prev.map(msg =>
          msg.id === assistantId
            ? { ...msg, content: msg.content + ' [Прервано]' }
            : msg
        ));
      } else {
        addLog('Ошибка генерации', 'error');
        console.error('Chat error:', error);
        setMessages(prev => prev.map(msg =>
          msg.id === assistantId
            ? { ...msg, content: `Ошибка: ${error.message || 'не удалось получить ответ'}` }
            : msg
        ));
      }
    } finally {
      setIsGenerating(false);
      setIsThinking(false);  // Ensure thinking is off
      setLoadingModel(null);  // Issue #6: Clear loading state
      abortControllerRef.current = null;
    }
  }

  function handleStopGeneration() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      addLog('Остановка генерации...', 'info');
    }
  }

  async function handleNewConversation() {
    const conv = await api.createConversation();
    setConversationId(conv.id);
    setMessages([
      { id: 1, role: 'system', content: 'Новый разговор начат. Чем могу помочь?', timestamp: formatTime(), model: 'System' }
    ]);
    addLog('Новый разговор создан', 'info');
    loadInitialData();
  }

  async function handleFeedback(messageId: number, rating: number) {
    setFeedbackSent(prev => ({ ...prev, [messageId]: rating > 0 ? 'up' : 'down' }));
    await api.submitFeedback(messageId, rating);
    if (rating > 0) {
      addLog('Эмпатия повышена: резонанс', 'empathy');
    } else {
      addLog('Feedback отправлен', 'info');
    }
    loadMetrics();
  }

  async function handleRegenerate(messageId: number) {
    // Find the user message before this assistant message
    const idx = messages.findIndex(m => m.id === messageId);
    if (idx > 0 && messages[idx - 1].role === 'user') {
      setInputVal(messages[idx - 1].content);
      setMessages(prev => prev.filter(m => m.id !== messageId));
      addLog('Regenerating response...', 'info');
    }
  }

  function handleCopy(content: string) {
    navigator.clipboard.writeText(content);
    addLog('Текст скопирован в буфер', 'info');
  }

  // ============= Document Handlers =============

  async function handleUploadDocument(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || isUploading) return;

    setIsUploading(true);
    try {
      await api.uploadDocument(file);
      addLog(`Файл "${file.name}" загружен`, 'growth');
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (error) {
      addLog('Ошибка загрузки файла', 'error');
    } finally {
      setIsUploading(false);
      // Reset input
      e.target.value = '';
    }
  }

  async function handleDeleteDocument() {
    await api.deleteDocument(deleteModal.docId);
    addLog(`Файл "${deleteModal.docName}" удален`, 'info');
    setDeleteModal({ isOpen: false, docId: '', docName: '' });
    const docs = await api.getDocuments();
    setDocuments(docs);
  }

  // ============= Agent Handlers =============

  function handleRequestAgent() {
    if (!agentGoal.trim() || agentRunning) return;
    setAgentConfirmModal(true);
  }

  async function handleConfirmAgent() {
    setAgentConfirmModal(false);
    if (!agentGoal.trim() || agentRunning) return;

    setAgentRunning(true);
    setAgentFailed(false); // Reset failed state on new run
    addLog('Автономный агент запущен', 'growth');

    try {
      await api.startAgent(agentGoal, 20);

      // Poll for status
      const pollInterval = setInterval(async () => {
        try {
          const status = await api.getAgentStatus();
          setAgentSteps(status.steps);

          if (!status.running) {
            clearInterval(pollInterval);
            setAgentRunning(false);
            // P3 Fix: Detect failed status for Retry button (STATE BUG #1)
            const hasFailed = status.steps?.some((s: { status: string }) => s.status === 'failed');
            if (hasFailed) {
              setAgentFailed(true);
              addLog('Агент не выполнил задачу', 'error');
            } else {
              addLog('Агент выполнил задачу', 'growth');
            }
            loadMetrics();
          }
        } catch {
          clearInterval(pollInterval);
          setAgentRunning(false);
          setAgentFailed(true);
          addLog('Ошибка при проверке статуса агента', 'error');
        }
      }, 2000);
    } catch (error) {
      setAgentRunning(false);
      setAgentFailed(true);
      addLog('Ошибка запуска агента', 'error');
    }
  }

  // ============= Template Handlers =============

  function handleUseTemplate(tpl: api.Template) {
    setActiveTab('chat');
    setInputVal(tpl.content);
    addLog(`Применен шаблон: ${tpl.name}`, 'info');
  }

  const filteredTemplates = tplCategory === 'All'
    ? templates
    : templates.filter(t => t.category === tplCategory);

  // ============= UI Components =============

  // ============= UI Components =============

  // TextAreaContainer, IconButton, ActionBtn moved to module level to fix focus bug

  const GlassCard = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
    <div className={`bg-zinc-900/40 backdrop-blur-md border border-white/5 rounded-2xl shadow-sm ${className}`}>
      {children}
    </div>
  );

  // Thinking Indicator with live timer
  const [thinkingElapsed, setThinkingElapsed] = useState(0);

  // Update thinking elapsed time every 100ms while thinking
  useEffect(() => {
    if (!isThinking) {
      setThinkingElapsed(0);
      return;
    }

    const interval = setInterval(() => {
      setThinkingElapsed((Date.now() - thinkingStartTime) / 1000);
    }, 100);

    return () => clearInterval(interval);
  }, [isThinking, thinkingStartTime]);

  const ThinkingIndicator = () => (
    <div className="flex items-center gap-4 p-5 bg-gradient-to-r from-indigo-950/60 to-purple-950/60 
                    border border-indigo-500/30 rounded-2xl backdrop-blur-xl shadow-lg shadow-indigo-500/10
                    max-w-sm animate-in fade-in slide-in-from-left-4 duration-500">
      {/* Animated brain icon with spinner */}
      <div className="relative flex-shrink-0">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-600/30 to-purple-600/30 
                        flex items-center justify-center">
          <span className="text-2xl">🧠</span>
        </div>
        {/* Spinning border */}
        <div className="absolute inset-0 rounded-full border-2 border-indigo-500/50 border-t-indigo-400 animate-spin"
          style={{ animationDuration: '1.5s' }} />
        {/* Pulsing glow */}
        <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping"
          style={{ animationDuration: '2s' }} />
      </div>

      {/* Text content */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-indigo-200">MAX думает</span>
          <span className="flex gap-0.5">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="font-mono tabular-nums">{thinkingElapsed.toFixed(1)}s</span>
          <span className="text-zinc-600">•</span>
          <span className="text-purple-400/80">Глубокий анализ</span>
        </div>
      </div>
    </div>
  );

  // Issue #6: Model loading indicator
  const ModelLoadingIndicator = () => {
    if (!loadingModel) return null;

    return (
      <div className="flex items-center gap-3 p-4 bg-gradient-to-r from-amber-950/60 to-orange-950/60 
                      border border-amber-500/30 rounded-xl backdrop-blur-xl
                      max-w-xs animate-in fade-in slide-in-from-left-4 duration-300">
        <Loader2 size={20} className="text-amber-400 animate-spin" />
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-amber-200">Загрузка модели</span>
          <span className="text-xs text-amber-400/70 truncate max-w-[180px]">{loadingModel}</span>
        </div>
      </div>
    );
  };


  // Collapsible Think Block (shows AI's reasoning process)
  const CollapsibleThink = () => {
    if (!thinkContent) return null;

    return (
      <div className="mb-4 animate-in fade-in slide-in-from-top-2 duration-300">
        <button
          onClick={() => setThinkExpanded(!thinkExpanded)}
          className="flex items-center gap-2 px-3 py-2 bg-purple-950/40 hover:bg-purple-950/60 
                     border border-purple-500/20 rounded-lg transition-all group w-full"
        >
          <span className="text-purple-400">🧠</span>
          <span className="text-sm text-purple-300/80">Процесс рассуждения</span>
          <ChevronDown
            size={14}
            className={`text-purple-400/60 ml-auto transition-transform duration-200 
                       ${thinkExpanded ? 'rotate-180' : ''}`}
          />
        </button>

        {thinkExpanded && (
          <div className="mt-2 p-4 bg-purple-950/20 border border-purple-500/10 rounded-lg
                          animate-in fade-in slide-in-from-top-1 duration-200">
            <pre className="text-xs text-purple-300/70 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto">
              {thinkContent}
            </pre>
          </div>
        )}
      </div>
    );
  };

  // Confidence Badge (shows AI's confidence in response)
  const ConfidenceBadge = () => {
    if (!lastConfidence) return null;

    const { score, level } = lastConfidence;
    const percent = Math.round(score * 100);

    // Color based on confidence level
    const colors = {
      high: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      low: 'bg-red-500/20 text-red-400 border-red-500/30'
    };

    const emoji = level === 'high' ? '🟢' : level === 'medium' ? '🟡' : '🔴';
    const colorClass = colors[level as keyof typeof colors] || colors.medium;

    return (
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium 
                       border ${colorClass} animate-in fade-in zoom-in-95 duration-300`}>
        <span>{emoji}</span>
        <span>{percent}% уверен</span>
      </div>
    );
  };

  // ============= Render =============

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#09090b] text-zinc-100 font-sans selection:bg-indigo-500/30">

      {/* Mobile Overlay */}
      {isMobile && sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        ${sidebarOpen ? 'w-80 translate-x-0' : 'w-20 -translate-x-full lg:translate-x-0'} 
        bg-[#09090b] border-r border-white/5 flex flex-col transition-all duration-500
      `}>
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/5 shrink-0">
          <div className="flex items-center">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-[0_0_15px_rgba(79,70,229,0.4)]">
              <Cpu size={20} className="text-white" />
            </div>
            {sidebarOpen && <span className="ml-3 font-bold text-xl tracking-tight text-white">MAX <span className="text-zinc-500 font-normal">AI</span></span>}
          </div>
          {sidebarOpen && <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-zinc-500 hover:text-white"><X size={20} /></button>}
        </div>

        {/* Chat & History */}
        <div className="flex-1 flex flex-col overflow-y-auto py-4 px-3 gap-1">
          <NavItem icon={<Plus size={18} />} label="Новый чат" active={false} onClick={handleNewConversation} collapsed={!sidebarOpen} />
          <NavItem icon={<MessageSquare size={18} />} label="Текущий чат" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} collapsed={!sidebarOpen} />

          {sidebarOpen && conversations.length > 0 && (
            <div className="mt-6 mb-2 px-2 flex items-center justify-between">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-wider">Недавние диалоги</span>
              <span className="text-[10px] text-zinc-700 bg-zinc-900 px-1.5 py-0.5 rounded-md border border-white/5">{conversations.length}</span>
            </div>
          )}

          <div className="space-y-0.5">
            {conversations.slice(0, 5).map(chat => (
              <button
                key={chat.id}
                onClick={() => { setConversationId(chat.id); setActiveTab('chat'); }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all group text-left hover:bg-zinc-900/50"
              >
                <MessageCircle size={16} className="text-zinc-500 group-hover:text-zinc-300" />
                {sidebarOpen && (
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-zinc-400 group-hover:text-zinc-200 truncate">{chat.title}</div>
                    <div className="text-[10px] text-zinc-600 truncate">{chat.message_count} сообщ.</div>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tools */}
        <div className="shrink-0 bg-[#09090b] border-t border-white/5 flex flex-col">
          <div className="px-3 py-4 space-y-1">
            {sidebarOpen && <div className="px-2 mb-2 text-[10px] font-bold text-zinc-600 uppercase tracking-wider">Инструменты</div>}
            <NavItem icon={<FileText size={18} />} label="База знаний (RAG)" active={activeTab === 'rag'} onClick={() => setActiveTab('rag')} collapsed={!sidebarOpen} />
            <NavItem icon={<Bot size={18} />} label="Авто-агент" active={activeTab === 'autogpt'} onClick={() => setActiveTab('autogpt')} collapsed={!sidebarOpen} />
            <NavItem icon={<LayoutTemplate size={18} />} label="Шаблоны" active={activeTab === 'templates'} onClick={() => setActiveTab('templates')} collapsed={!sidebarOpen} />
            <NavItem icon={<History size={18} />} label="Архив" active={activeTab === 'history'} onClick={() => setActiveTab('history')} collapsed={!sidebarOpen} />
          </div>

          {!sidebarOpen && (
            <button onClick={() => setSidebarOpen(true)} className="w-full flex items-center justify-center p-4 text-zinc-600 hover:text-white border-t border-white/5">
              <ChevronRight size={18} />
            </button>
          )}

          {/* The Living Core */}
          {sidebarOpen && (
            <div className="p-4 pt-2 border-t border-white/5 flex flex-col items-center">
              <SynapticStream logs={systemLogs} />
              <DenseCore intelligence={intelligence} empathy={empathy} />
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
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-2 -ml-2 text-zinc-400 hover:text-white rounded-lg">
              <Menu size={20} />
            </button>

            {activeTab === 'chat' ? (
              <div className="relative" ref={modelDropdownRef}>
                <button
                  onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                  className="flex items-center gap-2 cursor-pointer px-2 py-1.5 rounded-lg hover:bg-white/5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  aria-label="Выбрать модель"
                  aria-expanded={modelDropdownOpen}
                >
                  <span className="text-lg font-semibold text-white/90">MAX AI</span>
                  <span className="text-zinc-600">/</span>
                  <div className="flex items-center gap-2 text-sm text-zinc-300">
                    <span>{modelNames[selectedModel] || selectedModel}</span>
                    <ChevronDown size={14} className={`text-zinc-500 transition-transform ${modelDropdownOpen ? 'rotate-180' : ''}`} />
                  </div>
                </button>
                {modelDropdownOpen && (
                  <div className="absolute top-full left-0 mt-2 w-48 bg-zinc-900 border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden">
                    {availableModels.map(model => (
                      <button
                        key={model}
                        onClick={() => { setSelectedModel(model); setModelDropdownOpen(false); addLog(`Модель: ${model}`, 'info'); }}
                        className={`w-full px-4 py-2.5 text-left text-sm hover:bg-white/5 transition-colors flex items-center justify-between
                          ${selectedModel === model ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-300'}`}
                      >
                        {modelNames[model] || model}
                        {selectedModel === model && <Check size={14} />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <h2 className="text-lg font-semibold text-white/90">
                {activeTab === 'rag' && 'База Знаний'}
                {activeTab === 'autogpt' && 'Автономный Агент'}
                {activeTab === 'templates' && 'Галерея Шаблонов'}
                {activeTab === 'history' && 'Архив Событий'}
              </h2>
            )}
          </div>

          {/* Thinking Mode Selector */}
          {activeTab === 'chat' && (
            <div className="flex items-center gap-1 bg-zinc-800/50 rounded-full p-1">
              {thinkingModes.map(mode => (
                <button
                  key={mode.id}
                  onClick={() => { setThinkingMode(mode.id); addLog(`Режим: ${mode.label}`, 'info'); }}
                  className={`px-3 py-1 rounded-full text-sm transition-all duration-200 flex items-center gap-1
                    ${thinkingMode === mode.id
                      ? `${mode.bgActive} ${mode.color} font-medium`
                      : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'}`}
                  title={mode.label}
                >
                  <span>{mode.icon}</span>
                  <span className="hidden md:inline">{mode.label}</span>
                </button>
              ))}
              {/* Vision badge will show when image upload is implemented */}
            </div>
          )}

          <div className="flex items-center gap-3">
            <div className="relative hidden md:flex group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={15} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск..."
                className="w-64 bg-zinc-900/50 border border-white/5 rounded-lg py-1.5 pl-9 pr-4 text-sm text-zinc-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 placeholder:text-zinc-600"
                aria-label="Поиск по разговорам"
              />
            </div>

            {/* Backup Status Indicator */}
            <div className="hidden md:flex items-center gap-1.5 text-xs px-2 py-1 rounded-md bg-zinc-800/50">
              {backupStatus === 'synced' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-emerald-400">☁️ Синхронизировано</span>
                </>
              )}
              {backupStatus === 'syncing' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                  <span className="text-yellow-400">⏳ Синхронизация...</span>
                </>
              )}
              {backupStatus === 'error' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  <span className="text-red-400">⚠️ Ошибка</span>
                </>
              )}
              {backupStatus === 'unknown' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-zinc-500" />
                  <span className="text-zinc-500">💾 Локально</span>
                </>
              )}
            </div>

            {/* P3 Fix: Theme toggle with working handler */}
            <IconButton
              icon={darkMode ? <Sun size={18} /> : <Moon size={18} />}
              tooltip={darkMode ? "Светлая тема" : "Тёмная тема"}
              label="Переключить тему"
              onClick={() => {
                setDarkMode(!darkMode);
                // Future: Apply theme to document.documentElement
                addLog(`Тема: ${darkMode ? 'светлая' : 'тёмная'}`, 'info');
              }}
            />
          </div>
        </header>

        {/* Content Views */}
        <div className="flex-1 overflow-hidden relative">

          {/* CHAT VIEW */}
          {activeTab === 'chat' && (
            <div className="h-full flex flex-col max-w-4xl mx-auto w-full relative">
              <div className="flex-1 overflow-y-auto px-4 py-6">
                <div className="space-y-8 pb-4">
                  {messages.map((msg) => (
                    <div key={msg.id} className={`flex gap-4 md:gap-6 ${msg.role === 'user' ? 'flex-row-reverse' : ''} group`}>
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-1 shadow-lg ${msg.role === 'user' ? 'bg-zinc-800 text-zinc-400' : 'bg-gradient-to-br from-indigo-600 to-violet-700 text-white'
                        }`}>
                        {msg.role === 'user' ? <span className="text-xs font-bold">VM</span> : <Cpu size={16} />}
                      </div>
                      <div className={`flex flex-col max-w-[85%] md:max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div className="flex items-center gap-2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity select-none">
                          <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">{msg.role === 'user' ? 'You' : 'Max AI'}</span>
                          <span className="text-[10px] text-zinc-600">•</span>
                          <span className="text-[10px] text-zinc-600">{msg.timestamp}</span>
                        </div>
                        <div className={`prose prose-invert max-w-none text-sm leading-7 ${msg.role === 'user' ? 'text-zinc-100 text-right' : 'text-zinc-300'}`}>
                          {/* P3 Fix: Show More for long messages (DATA GAP #3) */}
                          {msg.content.length > 500 ? (
                            <details>
                              <summary className="cursor-pointer hover:text-zinc-100 list-none">
                                {msg.content.slice(0, 500).split('\n').map((line, i) => (
                                  <p key={i} className="mb-1 min-h-[1.5em] inline">{line || <br />}{i < msg.content.slice(0, 500).split('\n').length - 1 ? ' ' : ''}</p>
                                ))}
                                <span className="text-indigo-400 text-xs ml-1">... [Показать ещё {msg.content.length - 500} символов]</span>
                              </summary>
                              <div className="mt-2">
                                {msg.content.split('\n').map((line, i) => (
                                  <p key={i} className="mb-1 min-h-[1.5em]">{line || <br />}</p>
                                ))}
                              </div>
                            </details>
                          ) : (
                            msg.content.split('\n').map((line, i) => (
                              <p key={i} className="mb-1 min-h-[1.5em]">{line || <br />}</p>
                            ))
                          )}
                        </div>
                        {msg.role === 'assistant' && msg.content && (
                          <div className="flex items-center gap-1 mt-2.5 -ml-1.5">
                            <ActionBtn icon={<Copy size={14} />} onClick={() => handleCopy(msg.content)} label="Копировать" />
                            <ActionBtn icon={<RotateCw size={14} />} onClick={() => handleRegenerate(msg.id)} label="Перегенерировать" />
                            <div className="h-3 w-[1px] bg-white/10 mx-1" />
                            <button
                              onClick={() => handleFeedback(msg.id, 1)}
                              aria-label="Нравится"
                              className={`p-1.5 rounded-md transition-colors active:scale-90 ${feedbackSent[msg.id] === 'up' ? 'text-emerald-400 bg-emerald-500/20' : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800'}`}
                            >
                              {feedbackSent[msg.id] === 'up' ? <Check size={14} /> : <ThumbsUp size={14} />}
                            </button>
                            <button
                              onClick={() => handleFeedback(msg.id, -1)}
                              aria-label="Не нравится"
                              className={`p-1.5 rounded-md transition-colors active:scale-90 ${feedbackSent[msg.id] === 'down' ? 'text-red-400 bg-red-500/20' : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800'}`}
                            >
                              {feedbackSent[msg.id] === 'down' ? <Check size={14} /> : <ThumbsDown size={14} />}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {/* Show thinking indicator when model is thinking (reasoning) */}
                  {isThinking && (
                    <div className="pl-12 md:pl-14"><ThinkingIndicator /></div>
                  )}
                  {/* Issue #6: Show model loading indicator */}
                  {loadingModel && (
                    <div className="pl-12 md:pl-14"><ModelLoadingIndicator /></div>
                  )}
                  {/* Show simple generating indicator when generating but not thinking */}
                  {isGenerating && !isThinking && messages[messages.length - 1]?.role === 'assistant' && !messages[messages.length - 1]?.content && (
                    <div className="pl-12 md:pl-14">
                      <div className="flex items-center gap-2 p-3 text-zinc-500 text-sm">
                        <div className="w-4 h-4 border-2 border-zinc-600 border-t-indigo-400 rounded-full animate-spin" />
                        <span>Генерация...</span>
                      </div>
                    </div>
                  )}

                  {/* Collapsible Think Block - shows after response if thinking occurred */}
                  {!isGenerating && thinkContent && (
                    <div className="pl-12 md:pl-14 max-w-2xl">
                      <CollapsibleThink />
                    </div>
                  )}

                  {/* Confidence Badge - shows after response */}
                  {!isGenerating && lastConfidence && (
                    <div className="pl-12 md:pl-14 mt-2">
                      <ConfidenceBadge />
                    </div>
                  )}

                  <div ref={messagesEndRef} className="h-4" />
                </div>
              </div>

              {/* Input */}
              <div className="px-4 pb-6 pt-2 z-20">
                <div className="relative max-w-4xl mx-auto">
                  <TextAreaContainer isGenerating={isGenerating}>
                    <textarea
                      ref={textareaRef}
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendMessage())}
                      placeholder="Спроси о чем угодно..."
                      className="w-full bg-transparent border-none text-zinc-200 placeholder:text-zinc-500 px-5 py-4 min-h-[56px] max-h-[200px] resize-none focus:ring-0 text-[15px]"
                      rows={1}
                    />
                    <div className="flex items-center justify-between px-3 pb-3">
                      {/* P2 fix: Removed dead buttons (Plus/Globe) - features not yet implemented */}
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-zinc-600">Shift+Enter для новой строки</span>
                      </div>
                      <button
                        onClick={isGenerating ? handleStopGeneration : handleSendMessage}
                        disabled={!inputVal.trim() && !isGenerating}
                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all active:scale-90 ${inputVal.trim() || isGenerating ? 'bg-indigo-600 text-white hover:bg-indigo-500' : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                          }`}
                      >
                        {isGenerating ? <div className="w-3 h-3 bg-white rounded-sm" /> : <Send size={16} />}
                      </button>
                    </div>
                  </TextAreaContainer>
                </div>
              </div>
            </div>
          )}

          {/* RAG VIEW */}
          {activeTab === 'rag' && (
            <div className="p-4 md:p-8 max-w-6xl mx-auto h-full overflow-y-auto">
              <div className="flex justify-between items-end mb-8">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2">База Знаний</h1>
                  <p className="text-zinc-400">Управляйте документами для контекста RAG.</p>
                </div>
                <label className={`flex items-center gap-2 px-5 py-2.5 font-medium rounded-xl cursor-pointer transition-all ${isUploading ? 'bg-zinc-700 text-zinc-400 cursor-wait' : 'bg-white text-black hover:bg-zinc-200'}`}>
                  {isUploading ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                  <span>{isUploading ? 'Загрузка...' : 'Загрузить'}</span>
                  <input type="file" className="hidden" onChange={handleUploadDocument} disabled={isUploading} />
                </label>
              </div>
              <GlassCard className="overflow-hidden">
                <table className="w-full text-left border-collapse min-w-[600px]">
                  <thead>
                    <tr className="border-b border-white/5 bg-zinc-900/50">
                      <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider pl-6">Имя файла</th>
                      <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Тип</th>
                      <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Чанки</th>
                      <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Статус</th>
                      <th className="p-4" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {documents.map(doc => (
                      <tr key={doc.id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="p-4 pl-6">
                          <div className="flex items-center gap-4">
                            <FileText size={18} className="text-zinc-400" />
                            <span className="text-zinc-200 text-sm">{doc.name}</span>
                          </div>
                        </td>
                        <td className="p-4 text-zinc-500 text-xs">{doc.type}</td>
                        <td className="p-4 text-zinc-500 text-sm">{doc.chunks}</td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <div className={`w-1.5 h-1.5 rounded-full ${doc.status === 'indexed' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                            <span className="text-xs text-zinc-400 capitalize">{doc.status}</span>
                          </div>
                        </td>
                        <td className="p-4 text-right">
                          <button onClick={() => setDeleteModal({ isOpen: true, docId: doc.id, docName: doc.name })} className="p-2 text-zinc-600 hover:text-red-400">
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {documents.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-8 text-center text-zinc-600">Нет загруженных документов</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </GlassCard>
            </div>
          )}

          {/* AUTOGPT VIEW */}
          {activeTab === 'autogpt' && (
            <div className="p-4 md:p-8 max-w-5xl mx-auto h-full overflow-y-auto">
              <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div>
                  <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Автономный Агент</h1>
                  <p className="text-zinc-400">Делегируйте сложные задачи. Агент сам построит план и выполнит его.</p>
                </div>
              </div>

              <div className="grid lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2">
                  <GlassCard className="p-6">
                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-4 block">Цель миссии</label>
                    <textarea
                      value={agentGoal}
                      onChange={(e) => setAgentGoal(e.target.value)}
                      placeholder="Например: Найди последние новости о GPT-5 и составь сводку..."
                      className="w-full bg-zinc-950/50 border border-white/10 rounded-xl p-4 text-lg text-zinc-200 placeholder:text-zinc-700 focus:ring-1 focus:ring-indigo-500/50 resize-none min-h-[140px]"
                    />
                    <div className="flex flex-wrap items-center justify-end mt-6 gap-4">
                      {/* P3 Fix: Retry button for failed runs (STATE BUG #1) */}
                      {agentFailed && !agentRunning && (
                        <button
                          onClick={handleConfirmAgent}
                          className="px-6 py-3 rounded-xl font-medium text-sm flex items-center gap-2 transition-all shadow-lg bg-amber-600 text-white hover:bg-amber-500"
                        >
                          <RotateCw size={18} />
                          Повторить
                        </button>
                      )}
                      <button
                        onClick={handleRequestAgent}
                        disabled={!agentGoal.trim() || agentRunning}
                        className={`px-6 py-3 rounded-xl font-medium text-sm flex items-center gap-2 transition-all shadow-lg ${agentRunning ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed' : 'bg-white text-black hover:bg-zinc-200'
                          }`}
                      >
                        {agentRunning ? <div className="w-4 h-4 border-2 border-zinc-500 border-t-transparent rounded-full animate-spin" /> : <Play size={18} />}
                        {agentRunning ? 'Выполнение...' : 'Запустить Агента'}
                      </button>
                    </div>
                  </GlassCard>
                </div>

                <div className="px-2">
                  <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-4">Статус выполнения</h4>
                  <div className="relative border-l border-zinc-800 pl-8 space-y-8 ml-3">
                    {agentSteps.map((step) => (
                      <div key={step.id} className="relative">
                        <div className={`absolute -left-[39px] w-6 h-6 rounded-full border-2 flex items-center justify-center bg-[#09090b] ${step.status === 'completed' ? 'border-emerald-500 text-emerald-500' :
                          step.status === 'running' ? 'border-indigo-500 text-indigo-500 animate-pulse' :
                            'border-zinc-800 text-zinc-800'
                          }`}>
                          {step.status === 'completed' && <CheckCircle2 size={12} />}
                          {step.status === 'running' && <div className="w-2 h-2 bg-current rounded-full" />}
                        </div>
                        <div className={`transition-opacity ${step.status === 'pending' ? 'opacity-40' : 'opacity-100'}`}>
                          <div className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-1">{step.action}</div>
                          <div className="text-sm font-medium text-zinc-200">{step.title}</div>
                          {/* P3 Fix: Show action_input (previously hidden - DATA GAP #2) */}
                          {step.action_input && (
                            <details className="mt-2">
                              <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400">
                                Показать детали...
                              </summary>
                              <pre className="mt-1 text-xs text-zinc-400 bg-zinc-900/50 p-2 rounded overflow-x-auto max-h-32 overflow-y-auto">
                                {typeof step.action_input === 'string'
                                  ? step.action_input
                                  : JSON.stringify(step.action_input, null, 2)}
                              </pre>
                            </details>
                          )}
                          {step.status === 'running' && <div className="text-xs text-indigo-400 mt-1">В процессе...</div>}
                          {step.status === 'failed' && (
                            <div className="text-xs text-red-400 mt-1 flex items-center gap-1">
                              <AlertTriangle size={12} /> Ошибка
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {agentSteps.length === 0 && (
                      <div className="text-zinc-600 text-sm">Задайте цель и запустите агента</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
          }

          {/* TEMPLATES VIEW */}
          {
            activeTab === 'templates' && (
              <div className="p-4 md:p-8 max-w-6xl mx-auto h-full overflow-y-auto">
                <div className="flex justify-between items-center mb-8">
                  <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Галерея Шаблонов</h1>
                    <p className="text-zinc-400">Готовые промпты для ускорения работы.</p>
                  </div>
                  <button className="flex items-center gap-2 px-4 py-2 bg-zinc-900 border border-white/10 hover:bg-zinc-800 text-zinc-300 rounded-lg text-sm font-medium">
                    <Plus size={16} /> Создать свой
                  </button>
                </div>

                {/* Category Filter */}
                <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
                  {['All', 'Dev', 'Work', 'Creative'].map(cat => (
                    <button
                      key={cat}
                      onClick={() => setTplCategory(cat)}
                      className={`px-4 py-2 rounded-full text-xs font-medium transition-all border ${tplCategory === cat
                        ? 'bg-white text-black border-white'
                        : 'bg-transparent text-zinc-500 border-zinc-800 hover:border-zinc-600 hover:text-zinc-300'
                        }`}
                    >
                      {cat === 'All' ? 'Все' : cat === 'Dev' ? 'Разработка' : cat === 'Work' ? 'Бизнес' : 'Креатив'}
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredTemplates.map(tpl => (
                    <div
                      key={tpl.id}
                      onClick={() => handleUseTemplate(tpl)}
                      className="group relative bg-zinc-900/40 backdrop-blur-sm border border-white/5 rounded-2xl p-5 hover:border-indigo-500/30 transition-all cursor-pointer overflow-hidden"
                    >
                      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                      <div className="flex justify-between items-start mb-4 relative z-10">
                        <div className={`p-2 rounded-lg ${tpl.category === 'Dev' ? 'bg-blue-500/10 text-blue-400' :
                          tpl.category === 'Work' ? 'bg-emerald-500/10 text-emerald-400' :
                            'bg-purple-500/10 text-purple-400'
                          }`}>
                          {tpl.category === 'Dev' ? <Code size={18} /> :
                            tpl.category === 'Work' ? <Briefcase size={18} /> :
                              <PenTool size={18} />}
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-all transform group-hover:translate-x-0 translate-x-4">
                          <div className="p-1.5 bg-white/10 rounded-lg text-white hover:bg-indigo-600">
                            <ArrowRight size={14} />
                          </div>
                        </div>
                      </div>

                      <h3 className="text-sm font-semibold text-zinc-200 mb-2 group-hover:text-white relative z-10">{tpl.name}</h3>
                      <p className="text-xs text-zinc-500 line-clamp-2 leading-relaxed relative z-10 group-hover:text-zinc-400">
                        {tpl.content}
                      </p>
                    </div>
                  ))}
                  {filteredTemplates.length === 0 && (
                    <div className="col-span-full text-center text-zinc-600 py-12">
                      Нет шаблонов в этой категории
                    </div>
                  )}
                </div>
              </div>
            )
          }

          {/* HISTORY VIEW */}
          {
            activeTab === 'history' && (
              <div className="p-4 md:p-8 max-w-6xl mx-auto h-full overflow-y-auto">
                <div className="mb-8">
                  <h1 className="text-3xl font-bold text-white mb-2">Архив Событий</h1>
                  <p className="text-zinc-400">История всех взаимодействий с MAX AI.</p>
                </div>

                <GlassCard className="p-6">
                  <div className="space-y-4">
                    {/* P2 Fix: Filter conversations by searchQuery */}
                    {conversations
                      .filter(conv =>
                        !searchQuery.trim() ||
                        conv.title.toLowerCase().includes(searchQuery.toLowerCase())
                      )
                      .map(conv => (
                        <div
                          key={conv.id}
                          onClick={() => { setConversationId(conv.id); setActiveTab('chat'); }}
                          className="flex items-center justify-between p-4 rounded-xl bg-zinc-900/50 hover:bg-zinc-800/50 cursor-pointer transition-all border border-white/5 hover:border-white/10"
                        >
                          <div className="flex items-center gap-4">
                            <MessageSquare size={20} className="text-zinc-500" />
                            <div>
                              <div className="text-sm font-medium text-zinc-200">{conv.title}</div>
                              <div className="text-xs text-zinc-600">{conv.message_count} сообщений</div>
                            </div>
                          </div>
                          <div className="text-xs text-zinc-600">{new Date(conv.updated_at).toLocaleDateString()}</div>
                        </div>
                      ))}
                    {conversations.length === 0 && (
                      <div className="text-center text-zinc-600 py-12">Нет сохранённых разговоров</div>
                    )}
                  </div>
                </GlassCard>
              </div>
            )
          }
        </div >
      </main >

      {/* Delete Modal */}
      {
        deleteModal.isOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="bg-[#09090b] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-white mb-2">Удалить документ?</h3>
                <div className="text-zinc-400 text-sm mb-6">
                  Вы уверены, что хотите удалить <b className="text-white">{deleteModal.docName}</b>?
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setDeleteModal({ ...deleteModal, isOpen: false })}
                    className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-300 hover:bg-zinc-800"
                  >
                    Отмена
                  </button>
                  <button
                    onClick={handleDeleteDocument}
                    className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-500"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            </div>
          </div>
        )
      }
      {/* Agent Confirmation Modal */}
      {agentConfirmModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#09090b] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-amber-500/20">
                  <AlertTriangle size={20} className="text-amber-400" />
                </div>
                <h3 className="text-lg font-semibold text-white">Запустить агента?</h3>
              </div>
              <div className="text-zinc-400 text-sm mb-6">
                Автономный агент выполнит до <b className="text-white">20 шагов</b> для достижения цели.
                Это может занять несколько минут.
              </div>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setAgentConfirmModal(false)}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-zinc-300 hover:bg-zinc-800"
                >
                  Отмена
                </button>
                <button
                  onClick={handleConfirmAgent}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-black bg-white hover:bg-zinc-200 flex items-center gap-2"
                >
                  <Play size={16} /> Запустить
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
