/**
 * SafetyBanner Component Tests
 *
 * Tests the critical "Not medical advice" disclaimer banner
 * that must always be visible to users viewing insights.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SafetyBanner } from '../SafetyBanner'

describe('SafetyBanner', () => {
  it('renders the banner', () => {
    render(<SafetyBanner />)
    expect(screen.getByText('Not medical advice')).toBeInTheDocument()
  })

  it('displays the required disclaimer text', () => {
    render(<SafetyBanner />)
    expect(
      screen.getByText(/This app provides informational insights only/i)
    ).toBeInTheDocument()
  })

  it('warns about not diagnosing or treating conditions', () => {
    render(<SafetyBanner />)
    expect(
      screen.getByText(/does not diagnose or treat conditions/i)
    ).toBeInTheDocument()
  })

  it('advises seeking professional medical help', () => {
    render(<SafetyBanner />)
    expect(
      screen.getByText(/seek professional medical help/i)
    ).toBeInTheDocument()
  })

  it('has appropriate warning styling (red border)', () => {
    const { container } = render(<SafetyBanner />)
    const banner = container.firstChild as HTMLElement
    expect(banner.className).toContain('border-red-500')
    expect(banner.className).toContain('bg-red-50')
  })
})
