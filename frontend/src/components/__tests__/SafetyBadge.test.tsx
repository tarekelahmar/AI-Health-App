/**
 * SafetyBadge component tests
 *
 * Governance-critical: this badge surfaces risk level, evidence grade,
 * and boundary category to the user. These tests ensure:
 * - reasonable defaults when partial safety data is provided
 * - correct text content for each badge
 * - presence/absence behavior when safety is missing
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SafetyBadge, SafetyDetails } from '../SafetyBadge'
import type { SafetyDecision } from '../../types/Safety'

function makeSafety(overrides: Partial<SafetyDecision> = {}): Partial<SafetyDecision> {
  return {
    allowed: true,
    risk: 'moderate',
    boundary: 'experiment',
    evidence_grade: 'D',
    issues: [],
    ...overrides,
  }
}

describe('SafetyBadge', () => {
  it('renders nothing when safety is undefined', () => {
    const { container } = render(<SafetyBadge safety={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it('falls back to defaults when partial safety data is provided', () => {
    render(<SafetyBadge safety={{}} />)

    expect(screen.getByText(/Risk:/i)).toHaveTextContent('Risk: moderate')
    expect(screen.getByText(/Evidence:/i)).toHaveTextContent('Evidence: D')
    expect(screen.getByText(/Mode:/i)).toHaveTextContent('Mode: experiment')
  })

  it('renders risk, evidence, and boundary pills from safety decision', () => {
    const safety = makeSafety({
      risk: 'high',
      boundary: 'informational',
      evidence_grade: 'A',
    })

    render(<SafetyBadge safety={safety} />)

    expect(screen.getByText('Risk: high')).toBeInTheDocument()
    expect(screen.getByText('Evidence: A')).toBeInTheDocument()
    expect(screen.getByText('Mode: informational')).toBeInTheDocument()
  })
})

describe('SafetyDetails', () => {
  it('renders nothing when safety is undefined', () => {
    const { container } = render(<SafetyDetails safety={undefined} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when there are no issues', () => {
    const safety = makeSafety({ issues: [] })
    const { container } = render(<SafetyDetails safety={safety} />)
    expect(container.firstChild).toBeNull()
  })

  it('lists all safety issues with codes and messages', () => {
    const safety = makeSafety({
      issues: [
        { code: 'HIGH_RISK', severity: 'high', message: 'High risk detected' },
        { code: 'LOW_EVIDENCE', severity: 'moderate', message: 'Limited evidence' },
      ],
    })

    render(<SafetyDetails safety={safety} />)

    expect(screen.getByText('Safety notes')).toBeInTheDocument()
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('HIGH_RISK')
    expect(items[0]).toHaveTextContent('High risk detected')
    expect(items[1]).toHaveTextContent('LOW_EVIDENCE')
    expect(items[1]).toHaveTextContent('Limited evidence')
  })
})


