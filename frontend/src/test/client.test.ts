/**
 * Tests for API client functions
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock fetch
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

// Import after mocking
import * as api from '../api/client'

describe('API Client', () => {
    beforeEach(() => {
        mockFetch.mockClear()
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    describe('checkHealth', () => {
        it('returns health status object', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ status: 'ok', initialized: true })
            })

            const result = await api.checkHealth()

            expect(result.status).toBe('ok')
            expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/api/health')
        })

        it('throws when API is down', async () => {
            mockFetch.mockRejectedValueOnce(new Error('Network error'))

            await expect(api.checkHealth()).rejects.toThrow('Network error')
        })
    })

    describe('getConversations', () => {
        it('returns conversations list', async () => {
            const mockConversations = [
                { id: '1', title: 'Chat 1', message_count: 5, created_at: '2024-01-01', updated_at: '2024-01-01' },
                { id: '2', title: 'Chat 2', message_count: 3, created_at: '2024-01-02', updated_at: '2024-01-02' }
            ]

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockConversations
            })

            const result = await api.getConversations()

            expect(result).toHaveLength(2)
            expect(result[0].title).toBe('Chat 1')
        })
    })

    describe('createConversation', () => {
        it('creates and returns new conversation', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ id: 'new-conv-123' })
            })

            const result = await api.createConversation('Test Chat')

            expect(result.id).toBe('new-conv-123')
            expect(mockFetch).toHaveBeenCalledWith(
                'http://127.0.0.1:8000/api/conversations',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({ title: 'Test Chat' })
                })
            )
        })
    })

    describe('getDocuments', () => {
        it('returns documents list', async () => {
            const mockDocs = [
                { id: 'doc-1', name: 'file.txt', type: 'text', chunks: 5, status: 'indexed' }
            ]

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockDocs
            })

            const result = await api.getDocuments()

            expect(result).toHaveLength(1)
            expect(result[0].name).toBe('file.txt')
        })
    })

    describe('deleteDocument', () => {
        it('deletes document', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            })

            await api.deleteDocument('doc-123')

            expect(mockFetch).toHaveBeenCalledWith(
                'http://127.0.0.1:8000/api/documents/doc-123',
                expect.objectContaining({ method: 'DELETE' })
            )
        })
    })

    describe('getMetrics', () => {
        it('returns IQ and EQ metrics', async () => {
            const mockMetrics = {
                iq: { score: 75, components: {} },
                empathy: { score: 68, components: {} }
            }

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockMetrics
            })

            const result = await api.getMetrics()

            expect(result.iq.score).toBe(75)
            expect(result.empathy.score).toBe(68)
        })
    })

    describe('getTemplates', () => {
        it('returns templates list', async () => {
            const mockTemplates = [
                { id: 'tpl-1', name: 'Code Review', content: 'Review: {code}', category: 'Dev' }
            ]

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockTemplates
            })

            const result = await api.getTemplates()

            expect(result).toHaveLength(1)
            expect(result[0].name).toBe('Code Review')
        })
    })

    describe('submitFeedback', () => {
        it('submits positive feedback', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            })

            await api.submitFeedback(1, 1)

            expect(mockFetch).toHaveBeenCalledWith(
                'http://127.0.0.1:8000/api/feedback',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({ message_id: 1, rating: 1 })
                })
            )
        })

        it('submits negative feedback', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ success: true })
            })

            await api.submitFeedback(1, -1)

            expect(mockFetch).toHaveBeenCalledWith(
                'http://127.0.0.1:8000/api/feedback',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({ message_id: 1, rating: -1 })
                })
            )
        })
    })

    describe('startAgent', () => {
        it('starts agent with goal', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ run_id: 'test-run-123', goal: 'Test goal' })
            })

            const result = await api.startAgent('Test goal', 20)

            expect(result).toBeDefined()
            expect(mockFetch).toHaveBeenCalledWith(
                'http://127.0.0.1:8000/api/agent/start',
                expect.objectContaining({
                    method: 'POST'
                })
            )
        })
    })

    describe('getAgentStatus', () => {
        it('returns agent status', async () => {
            const mockStatus = {
                running: true,
                goal: 'Test goal',
                steps: [
                    { id: 1, action: 'search', title: 'Searching...', status: 'completed' }
                ],
                current_step: 1
            }

            mockFetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockStatus
            })

            const result = await api.getAgentStatus()

            expect(result.running).toBe(true)
            expect(result.steps).toHaveLength(1)
        })
    })
})
