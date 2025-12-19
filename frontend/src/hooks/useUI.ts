/**
 * UI Hook — manages UI state like sidebar, theme, logs.
 * 
 * FIX: Limited logs array to prevent OOM, added localStorage for sidebar.
 */
import { useState, useCallback, useEffect } from 'react';
import type { LogEntry } from '../components/SynapticStream';

// FIX: Max logs to prevent memory leak
const MAX_LOGS = 100;
const STORAGE_KEY_SIDEBAR = 'max_sidebar_open';
const STORAGE_KEY_DARKMODE = 'max_dark_mode'; // UX-018

export function useUI() {
    const [activeTab, setActiveTab] = useState<'chat' | 'rag' | 'research' | 'autogpt' | 'templates' | 'history'>('chat');
    // FIX: Initialize sidebarOpen from localStorage on desktop
    const [sidebarOpen, setSidebarOpen] = useState(() => {
        if (typeof window !== 'undefined' && window.innerWidth >= 1024) {
            const stored = localStorage.getItem(STORAGE_KEY_SIDEBAR);
            return stored !== null ? stored === 'true' : true;
        }
        return true;
    });
    const [isMobile, setIsMobile] = useState(false);
    // UX-018: Dark mode with localStorage persistence
    const [darkMode, setDarkModeState] = useState(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY_DARKMODE);
            return stored !== null ? stored === 'true' : true;
        } catch { return true; }
    });
    const [systemLogs, setSystemLogs] = useState<LogEntry[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [brainFullscreen, setBrainFullscreen] = useState(false);

    // Responsive handling
    useEffect(() => {
        const handleResize = () => {
            const mobile = window.innerWidth < 1024;
            setIsMobile(mobile);
            if (mobile) {
                setSidebarOpen(false);
            } else {
                // FIX: On desktop, restore from localStorage
                const stored = localStorage.getItem(STORAGE_KEY_SIDEBAR);
                setSidebarOpen(stored !== null ? stored === 'true' : true);
            }
        };
        handleResize();
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // FIX: Persist sidebarOpen to localStorage on desktop
    useEffect(() => {
        if (!isMobile) {
            localStorage.setItem(STORAGE_KEY_SIDEBAR, String(sidebarOpen));
        }
    }, [sidebarOpen, isMobile]);

    // FIX: Limited logs to MAX_LOGS to prevent memory leak
    const addLog = useCallback((text: string, type: LogEntry['type'] = 'info') => {
        const newLog: LogEntry = {
            id: Date.now(),
            text,
            type,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        // FIX: Slice to keep only last MAX_LOGS entries
        setSystemLogs(prev => [...prev.slice(-(MAX_LOGS - 1)), newLog]);
    }, []);

    const toggleSidebar = useCallback(() => {
        setSidebarOpen(prev => !prev);
    }, []);

    // UX-018: Toggle dark mode with localStorage persistence
    const toggleDarkMode = useCallback(() => {
        setDarkModeState((prev: boolean) => {
            const newValue = !prev;
            try {
                localStorage.setItem(STORAGE_KEY_DARKMODE, String(newValue));
            } catch { /* ignore */ }
            return newValue;
        });
    }, []);

    // FIX: Add clearLogs function
    const clearLogs = useCallback(() => {
        setSystemLogs([]);
    }, []);

    // Toggle fullscreen Brain Map mode
    const toggleBrainFullscreen = useCallback(() => {
        setBrainFullscreen(prev => !prev);
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
        clearLogs, // FIX: Expose clearLogs

        // Search
        searchQuery,
        setSearchQuery,

        // Brain Map fullscreen
        brainFullscreen,
        setBrainFullscreen,
        toggleBrainFullscreen,
    };
}
