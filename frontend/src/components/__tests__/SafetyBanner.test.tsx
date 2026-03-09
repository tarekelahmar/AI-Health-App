/**
 * SafetyBanner component tests
 *
 * Governance-critical: this banner must clearly communicate that the
 * product is NOT providing medical advice.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SafetyBanner } from '../SafetyBanner'

describe('SafetyBanner', () => {
  it('renders the primary heading', () => {
    render(<SafetyBanner />)
    expect(screen.getByText('Not medical advice')).toBeInTheDocument()
  })

  it('includes the required disclaimer language', () => {
    render(<SafetyBanner />)

    expect(
      screen.getByText(/informational insights only/i),
    ).toBeInTheDocument()

    expect(
      screen.getByText(/does not diagnose or treat conditions/i),
    ).toBeInTheDocument()

    expect(
      screen.getByText(/seek professional medical help/i),
    ).toBeInTheDocument()
  })
})


