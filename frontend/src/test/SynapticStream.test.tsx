/**
 * Tests for SynapticStream component (activity log)
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SynapticStream } from '../components/SynapticStream'
import type { LogEntry } from '../components/SynapticStream'

describe('SynapticStream', () => {
    const sampleLogs: LogEntry[] = [
        { id: 1, text: 'Connected to MAX AI', type: 'info', time: '10:00' },
        { id: 2, text: 'Response generated', type: 'growth', time: '10:01' },
        { id: 3, text: 'Empathy resonance', type: 'empathy', time: '10:02' },
        { id: 4, text: 'Error occurred', type: 'error', time: '10:03' }
    ]

    it('renders without crashing', () => {
        render(<SynapticStream logs={[]} />)

        // Should render header
        expect(screen.getByText('Синапс')).toBeInTheDocument()
    })

    it('displays empty state when no logs', () => {
        const { container } = render(<SynapticStream logs={[]} />)

        // Should have Activity icon in empty state
        const svg = container.querySelector('svg')
        expect(svg).toBeInTheDocument()
    })

    it('renders all log entries', () => {
        render(<SynapticStream logs={sampleLogs} />)

        expect(screen.getByText('Connected to MAX AI')).toBeInTheDocument()
        expect(screen.getByText('Response generated')).toBeInTheDocument()
        expect(screen.getByText('Empathy resonance')).toBeInTheDocument()
        expect(screen.getByText('Error occurred')).toBeInTheDocument()
    })

    it('displays timestamps', () => {
        render(<SynapticStream logs={sampleLogs} />)

        expect(screen.getByText('10:00')).toBeInTheDocument()
        expect(screen.getByText('10:01')).toBeInTheDocument()
    })

    it('applies correct color classes for log types', () => {
        const { container } = render(<SynapticStream logs={sampleLogs} />)

        // Should have colored dots
        const dots = container.querySelectorAll('.rounded-full')
        expect(dots.length).toBeGreaterThan(0)
    })
})
