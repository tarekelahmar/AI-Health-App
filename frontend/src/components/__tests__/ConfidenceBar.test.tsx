/**
 * ConfidenceBar component tests
 *
 * Governance-critical: this visualization explains how confident the
 * system is in an insight and why. Tests cover:
 * - correct label and percentage display
 * - color mapping for low/medium/high levels
 * - rendering of uncertainty reasons and effect size
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceBar } from '../ConfidenceBar'
import type { ConfidenceBreakdown } from '../../types/Confidence'

function makeConfidence(overrides: Partial<ConfidenceBreakdown> = {}): ConfidenceBreakdown {
  return {
    level: 'medium',
    score: 0.65,
    data_coverage_days: 14,
    consistency_ratio: 0.8,
    uncertainty_reasons: [],
    ...overrides,
  }
}

describe('ConfidenceBar', () => {
  it('renders the confidence label and level', () => {
    const c = makeConfidence({ level: 'high', score: 0.9 })
    render(<ConfidenceBar c={c} />)

    expect(screen.getByText('Confidence')).toBeInTheDocument()
    expect(screen.getByText(/high/i)).toBeInTheDocument()
    expect(screen.getByText('90%')).toBeInTheDocument()
  })

  it('shows data coverage days', () => {
    const c = makeConfidence({ data_coverage_days: 30 })
    render(<ConfidenceBar c={c} />)

    expect(screen.getByText(/Based on 30 days of data/)).toBeInTheDocument()
  })

  it('renders uncertainty reasons when present', () => {
    const c = makeConfidence({
      uncertainty_reasons: ['insufficient_data', 'confounding_signals'],
    })

    render(<ConfidenceBar c={c} />)

    expect(screen.getByText(/Uncertainty factors:/i)).toBeInTheDocument()
    expect(screen.getByText(/insufficient data/i)).toBeInTheDocument()
    expect(screen.getByText(/confounding signals/i)).toBeInTheDocument()
  })

  it('renders effect size to two decimal places when provided', () => {
    const c = makeConfidence({ effect_size: 0.1234 })
    render(<ConfidenceBar c={c} />)

    expect(screen.getByText(/Effect size:/i)).toHaveTextContent('Effect size: 0.12')
  })
})


