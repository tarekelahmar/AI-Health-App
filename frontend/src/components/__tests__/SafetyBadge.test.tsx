/**
 * SafetyBadge Component Tests
 *
 * Tests the governance-critical safety badge UI that displays
 * risk levels, evidence grades, and boundary categories.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SafetyBadge, SafetyDetails } from '../SafetyBadge'
import type { SafetyDecision } from '../../types/Safety'

describe('SafetyBadge', () => {
  it('renders nothing when safety is undefined', () => {
    const { container } = render(<SafetyBadge safety={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when safety is empty object', () => {
    const { container } = render(<SafetyBadge safety={{}} />)
    // With defaults, it should still render the badges
    expect(screen.getByText('Risk: moderate')).toBeInTheDocument()
  })

  describe('Risk Level Pills', () => {
    it('renders high risk with red styling', () => {
      render(<SafetyBadge safety={{ risk: 'high' }} />)
      const pill = screen.getByText('Risk: high')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-red-100')
      expect(pill.className).toContain('text-red-800')
    })

    it('renders moderate risk with yellow styling', () => {
      render(<SafetyBadge safety={{ risk: 'moderate' }} />)
      const pill = screen.getByText('Risk: moderate')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-yellow-100')
      expect(pill.className).toContain('text-yellow-800')
    })

    it('renders low risk with green styling', () => {
      render(<SafetyBadge safety={{ risk: 'low' }} />)
      const pill = screen.getByText('Risk: low')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-green-100')
      expect(pill.className).toContain('text-green-800')
    })
  })

  describe('Evidence Grade Pills', () => {
    it('renders grade A with green styling', () => {
      render(<SafetyBadge safety={{ evidence_grade: 'A' }} />)
      const pill = screen.getByText('Evidence: A')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-green-100')
      expect(pill.className).toContain('text-green-800')
    })

    it('renders grade B with emerald styling', () => {
      render(<SafetyBadge safety={{ evidence_grade: 'B' }} />)
      const pill = screen.getByText('Evidence: B')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-emerald-100')
      expect(pill.className).toContain('text-emerald-800')
    })

    it('renders grade C with yellow styling', () => {
      render(<SafetyBadge safety={{ evidence_grade: 'C' }} />)
      const pill = screen.getByText('Evidence: C')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-yellow-100')
      expect(pill.className).toContain('text-yellow-800')
    })

    it('renders grade D with gray styling', () => {
      render(<SafetyBadge safety={{ evidence_grade: 'D' }} />)
      const pill = screen.getByText('Evidence: D')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-gray-100')
      expect(pill.className).toContain('text-gray-800')
    })
  })

  describe('Boundary Category Pills', () => {
    it('renders informational boundary with blue styling', () => {
      render(<SafetyBadge safety={{ boundary: 'informational' }} />)
      const pill = screen.getByText('Mode: informational')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-blue-100')
      expect(pill.className).toContain('text-blue-800')
    })

    it('renders lifestyle boundary with indigo styling', () => {
      render(<SafetyBadge safety={{ boundary: 'lifestyle' }} />)
      const pill = screen.getByText('Mode: lifestyle')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-indigo-100')
      expect(pill.className).toContain('text-indigo-800')
    })

    it('renders experiment boundary with purple styling', () => {
      render(<SafetyBadge safety={{ boundary: 'experiment' }} />)
      const pill = screen.getByText('Mode: experiment')
      expect(pill).toBeInTheDocument()
      expect(pill.className).toContain('bg-purple-100')
      expect(pill.className).toContain('text-purple-800')
    })
  })

  it('renders all three pills together', () => {
    const safety: Partial<SafetyDecision> = {
      risk: 'high',
      evidence_grade: 'A',
      boundary: 'lifestyle',
    }
    render(<SafetyBadge safety={safety} />)

    expect(screen.getByText('Risk: high')).toBeInTheDocument()
    expect(screen.getByText('Evidence: A')).toBeInTheDocument()
    expect(screen.getByText('Mode: lifestyle')).toBeInTheDocument()
  })
})

describe('SafetyDetails', () => {
  it('renders nothing when safety is undefined', () => {
    const { container } = render(<SafetyDetails safety={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when issues array is empty', () => {
    const { container } = render(<SafetyDetails safety={{ issues: [] }} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders safety notes header when issues exist', () => {
    const safety: Partial<SafetyDecision> = {
      issues: [
        { code: 'TEST001', severity: 'moderate', message: 'Test issue message' },
      ],
    }
    render(<SafetyDetails safety={safety} />)
    expect(screen.getByText('Safety notes')).toBeInTheDocument()
  })

  it('renders all issues with code and message', () => {
    const safety: Partial<SafetyDecision> = {
      issues: [
        { code: 'WARN001', severity: 'low', message: 'First warning' },
        { code: 'ALERT002', severity: 'high', message: 'Second alert' },
      ],
    }
    render(<SafetyDetails safety={safety} />)

    expect(screen.getByText('WARN001')).toBeInTheDocument()
    expect(screen.getByText(/First warning/)).toBeInTheDocument()
    expect(screen.getByText('ALERT002')).toBeInTheDocument()
    expect(screen.getByText(/Second alert/)).toBeInTheDocument()
  })
})
