// Shared types for MAX AI components

export interface Message {
    id: number;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;  // Optional to match actual usage in ChatTab
    model?: string;
}

export interface ThinkingModeConfig {
    id: 'fast' | 'standard' | 'deep';
    icon: string;
    label: string;
    color: string;
    bgActive: string;
}

export interface ConfidenceInfo {
    score: number;
    level: 'high' | 'medium' | 'low';
}
