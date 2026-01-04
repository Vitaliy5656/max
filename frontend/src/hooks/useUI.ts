/**
 * UI Hook — manages UI state like sidebar, theme, logs.
 */
import { useState, useCallback, useEffect } from 'react';
import type { LogEntry } from '../components/SynapticStream';

export function useUI() {
    const [activeTab, setActiveTab] = useState<'chat' | 'rag' | 'autogpt' | 'templates' | 'history'>('chat');
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [isMobile, setIsMobile] = useState(false);
    const [darkMode, setDarkMode] = useState(true);
    const [systemLogs, setSystemLogs] = useState<LogEntry[]>([]);
    const [searchQuery, setSearchQuery] = useState('');

    // Responsive handling
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

    const addLog = useCallback((text: string, type: LogEntry['type'] = 'info') => {
        const newLog: LogEntry = {
            id: Date.now(),
            text,
            type,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setSystemLogs(prev => [...prev, newLog]);
    }, []);

    const toggleSidebar = useCallback(() => {
        setSidebarOpen(prev => !prev);
    }, []);

    const toggleDarkMode = useCallback(() => {
        setDarkMode(prev => !prev);
    }, []);

    return {
        // Navigation
        activeTab,
        setActiveTab,

        // Sidebar
        sidebarOpen,
        setSidebarOpen,
        toggleSidebar,
        isMobile,

        // Theme
        darkMode,
        toggleDarkMode,

        // Logs
        systemLogs,
        addLog,

        // Search
        searchQuery,
        setSearchQuery,
    };
}
