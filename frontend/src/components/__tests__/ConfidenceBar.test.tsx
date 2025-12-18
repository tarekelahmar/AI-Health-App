/**
 * ConfidenceBar Component Tests
 *
 * Tests the confidence visualization component that shows
 * users how much they can trust an insight, with uncertainty factors.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceBar } from '../ConfidenceBar'
import type { ConfidenceBreakdown, UncertaintyReason } from '../../types/Confidence'

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
  describe('Level Display', () => {
    it('displays high confidence level', () => {
      render(<ConfidenceBar c={makeConfidence({ level: 'high' })} />)
      expect(screen.getByText('high')).toBeInTheDocument()
    })

    it('displays medium confidence level', () => {
      render(<ConfidenceBar c={makeConfidence({ level: 'medium' })} />)
      expect(screen.getByText('medium')).toBeInTheDocument()
    })

    it('displays low confidence level', () => {
      render(<ConfidenceBar c={makeConfidence({ level: 'low' })} />)
      expect(screen.getByText('low')).toBeInTheDocument()
    })
  })

  describe('Color Coding', () => {
    it('uses green for high confidence', () => {
      const { container } = render(
        <ConfidenceBar c={makeConfidence({ level: 'high', score: 0.9 })} />
      )
      const progressBar = container.querySelector('.bg-green-500')
      expect(progressBar).toBeInTheDocument()
    })

    it('uses yellow for medium confidence', () => {
      const { container } = render(
        <ConfidenceBar c={makeConfidence({ level: 'medium', score: 0.6 })} />
      )
      const progressBar = container.querySelector('.bg-yellow-500')
      expect(progressBar).toBeInTheDocument()
    })

    it('uses red for low confidence', () => {
      const { container } = render(
        <ConfidenceBar c={makeConfidence({ level: 'low', score: 0.3 })} />
      )
      const progressBar = container.querySelector('.bg-red-500')
      expect(progressBar).toBeInTheDocument()
    })
  })

  describe('Percentage Display', () => {
    it('shows percentage rounded to nearest integer', () => {
      render(<ConfidenceBar c={makeConfidence({ score: 0.756 })} />)
      expect(screen.getByText('76%')).toBeInTheDocument()
    })

    it('shows 100% for score of 1.0', () => {
      render(<ConfidenceBar c={makeConfidence({ score: 1.0 })} />)
      expect(screen.getByText('100%')).toBeInTheDocument()
    })

    it('shows 0% for score of 0', () => {
      render(<ConfidenceBar c={makeConfidence({ score: 0 })} />)
      expect(screen.getByText('0%')).toBeInTheDocument()
    })
  })

  describe('Data Coverage', () => {
    it('shows days of data coverage', () => {
      render(<ConfidenceBar c={makeConfidence({ data_coverage_days: 30 })} />)
      expect(screen.getByText(/Based on 30 days of data/i)).toBeInTheDocument()
    })

    it('shows singular day correctly', () => {
      render(<ConfidenceBar c={makeConfidence({ data_coverage_days: 1 })} />)
      expect(screen.getByText(/Based on 1 days of data/i)).toBeInTheDocument()
    })
  })

  describe('Uncertainty Reasons', () => {
    it('hides uncertainty section when no reasons', () => {
      render(<ConfidenceBar c={makeConfidence({ uncertainty_reasons: [] })} />)
      expect(screen.queryByText(/Uncertainty factors/i)).not.toBeInTheDocument()
    })

    it('shows uncertainty reasons when present', () => {
      const reasons: UncertaintyReason[] = ['insufficient_data', 'high_variability']
      render(<ConfidenceBar c={makeConfidence({ uncertainty_reasons: reasons })} />)
      expect(screen.getByText(/Uncertainty factors/i)).toBeInTheDocument()
      expect(screen.getByText(/insufficient data/i)).toBeInTheDocument()
      expect(screen.getByText(/high variability/i)).toBeInTheDocument()
    })

    it('replaces underscores with spaces in reason display', () => {
      const reasons: UncertaintyReason[] = ['confounding_signals']
      render(<ConfidenceBar c={makeConfidence({ uncertainty_reasons: reasons })} />)
      expect(screen.getByText(/confounding signals/i)).toBeInTheDocument()
    })
  })

  describe('Effect Size', () => {
    it('hides effect size when undefined', () => {
      render(<ConfidenceBar c={makeConfidence({ effect_size: undefined })} />)
      expect(screen.queryByText(/Effect size/i)).not.toBeInTheDocument()
    })

    it('shows effect size when present', () => {
      render(<ConfidenceBar c={makeConfidence({ effect_size: 0.45 })} />)
      expect(screen.getByText(/Effect size: 0.45/i)).toBeInTheDocument()
    })

    it('formats effect size to 2 decimal places', () => {
      render(<ConfidenceBar c={makeConfidence({ effect_size: 0.12345 })} />)
      expect(screen.getByText(/Effect size: 0.12/i)).toBeInTheDocument()
    })
  })

  describe('Progress Bar Width', () => {
    it('sets progress bar width based on score', () => {
      const { container } = render(
        <ConfidenceBar c={makeConfidence({ level: 'high', score: 0.75 })} />
      )
      const progressBar = container.querySelector('[style*="width"]') as HTMLElement
      expect(progressBar?.style.width).toBe('75%')
    })
  })
})
