/**
 * Tests for main App component
 * 
 * Simplified tests that focus on component rendering
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
    MessageSquare: () => <span data-testid="icon-message-square" />,
    FileText: () => <span data-testid="icon-file-text" />,
    Bot: () => <span data-testid="icon-bot" />,
    LayoutTemplate: () => <span data-testid="icon-layout-template" />,
    Search: () => <span data-testid="icon-search" />,
    Plus: () => <span data-testid="icon-plus" />,
    Send: () => <span data-testid="icon-send" />,
    Cpu: () => <span data-testid="icon-cpu" />,
    Trash2: () => <span data-testid="icon-trash" />,
    Play: () => <span data-testid="icon-play" />,
    CheckCircle2: () => <span data-testid="icon-check" />,
    History: () => <span data-testid="icon-history" />,
    ChevronDown: () => <span data-testid="icon-chevron-down" />,
    Copy: () => <span data-testid="icon-copy" />,
    RotateCw: () => <span data-testid="icon-rotate" />,
    ThumbsUp: () => <span data-testid="icon-thumbs-up" />,
    ThumbsDown: () => <span data-testid="icon-thumbs-down" />,
    Sparkles: () => <span data-testid="icon-sparkles" />,
    Globe: () => <span data-testid="icon-globe" />,
    Sun: () => <span data-testid="icon-sun" />,
    Menu: () => <span data-testid="icon-menu" />,
    X: () => <span data-testid="icon-x" />,
    MessageCircle: () => <span data-testid="icon-message-circle" />,
    Code: () => <span data-testid="icon-code" />,
    Briefcase: () => <span data-testid="icon-briefcase" />,
    PenTool: () => <span data-testid="icon-pen-tool" />,
    ArrowRight: () => <span data-testid="icon-arrow-right" />,
    ChevronRight: () => <span data-testid="icon-chevron-right" />,
    Check: () => <span data-testid="icon-check-small" />,
    Loader2: () => <span data-testid="icon-loader" />,
    AlertTriangle: () => <span data-testid="icon-alert" />,
    Activity: () => <span data-testid="icon-activity" />,
    BrainCircuit: () => <span data-testid="icon-brain" />,
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
}))

import App from '../App'

describe('App Component', () => {
    beforeEach(() => {
        mockFetch.mockClear()

        // Default mock responses
        mockFetch.mockImplementation(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve([])
            })
        )
    })

    it('renders MAX AI header', () => {
        render(<App />)

        // Should render MAX in header
        expect(screen.getByText('MAX')).toBeInTheDocument()
    })

    it('renders sidebar navigation', () => {
        render(<App />)

        // Check for sidebar buttons by text content
        expect(screen.getByText('Новый чат')).toBeInTheDocument()
        expect(screen.getByText('Текущий чат')).toBeInTheDocument()
    })

    it('renders Инструменты section', () => {
        render(<App />)

        expect(screen.getByText('Инструменты')).toBeInTheDocument()
    })

    it('has textarea for chat input', () => {
        render(<App />)

        // Find textarea by role
        const textareas = document.querySelectorAll('textarea')
        expect(textareas.length).toBeGreaterThan(0)
    })

    it('renders all main navigation buttons', () => {
        render(<App />)

        // Check tools section has all buttons
        expect(screen.getByText('База знаний (RAG)')).toBeInTheDocument()
        expect(screen.getByText('Авто-агент')).toBeInTheDocument()
        expect(screen.getByText('Шаблоны')).toBeInTheDocument()
    })

    it('has multiple buttons for interaction', () => {
        render(<App />)

        const buttons = screen.getAllByRole('button')

        // Should have many interactive buttons
        expect(buttons.length).toBeGreaterThan(5)
    })
})

describe('App Component Icons', () => {
    beforeEach(() => {
        mockFetch.mockImplementation(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve([])
            })
        )
    })

    it('renders navigation icons', () => {
        render(<App />)

        // Check that our mocked icons are rendered (may have multiple instances)
        expect(screen.getAllByTestId('icon-cpu').length).toBeGreaterThan(0)
        expect(screen.getAllByTestId('icon-file-text').length).toBeGreaterThan(0)
        expect(screen.getAllByTestId('icon-bot').length).toBeGreaterThan(0)
    })

    it('renders layout template icon', () => {
        render(<App />)

        expect(screen.getByTestId('icon-layout-template')).toBeInTheDocument()
    })

    it('renders history icon', () => {
        render(<App />)

        expect(screen.getByTestId('icon-history')).toBeInTheDocument()
    })
})
