/**
 * Tests for DenseCore component (IQ/EQ visualization)
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DenseCore } from '../components/DenseCore'

describe('DenseCore', () => {
    it('renders without crashing', () => {
        render(<DenseCore intelligence={50} empathy={50} />)

        // Should render IQ and EQ labels
        expect(screen.getByText('IQ')).toBeInTheDocument()
        expect(screen.getByText('EQ')).toBeInTheDocument()
    })

    it('displays correct IQ percentage', () => {
        render(<DenseCore intelligence={75} empathy={50} />)

        expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('displays correct EQ percentage', () => {
        render(<DenseCore intelligence={50} empathy={68} />)

        expect(screen.getByText('68%')).toBeInTheDocument()
    })

    it('handles zero values', () => {
        render(<DenseCore intelligence={0} empathy={0} />)

        // Both show 0%
        expect(screen.getAllByText('0%')).toHaveLength(2)
    })

    it('handles 100% values', () => {
        render(<DenseCore intelligence={100} empathy={100} />)

        expect(screen.getAllByText('100%')).toHaveLength(2)
    })

    it('renders SVG orbits', () => {
        const { container } = render(<DenseCore intelligence={50} empathy={50} />)

        // Should have SVG element
        const svg = container.querySelector('svg')
        expect(svg).toBeInTheDocument()

        // Should have circle elements for orbits
        const circles = container.querySelectorAll('circle')
        expect(circles.length).toBeGreaterThan(0)
    })
})
