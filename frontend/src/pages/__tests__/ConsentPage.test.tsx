/**
 * ConsentPage tests
 *
 * Governance-critical: users must complete consent (all 4 checkboxes)
 * before accessing the app. These tests verify:
 * - redirect to /login when no userId
 * - pre-existing completed consent triggers redirect to /connect
 * - submit button is disabled until all checkboxes are checked
 * - successful submission calls createConsent + completeOnboarding and navigates
 */

import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import ConsentPage from '../ConsentPage'
import * as consentApi from '../../api/consent'
import * as AuthContext from '../../contexts/AuthContext'

// Spy on consent API functions
vi.mock('../../api/consent', async (orig) => {
  const actual = await orig()
  return {
    ...actual,
    getConsent: vi.fn(),
    createConsent: vi.fn(),
    completeOnboarding: vi.fn(),
  }
})

describe('ConsentPage', () => {
  const user = userEvent.setup()
  let useAuthSpy: vi.SpyInstance | undefined

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
    useAuthSpy?.mockRestore()
  })

  it('redirects to /login when there is no userId', async () => {
    useAuthSpy = vi
      .spyOn(AuthContext, 'useAuth')
      .mockReturnValue({ userId: null, setUserId: vi.fn(), isAuthenticated: false })

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route path="/consent" element={<ConsentPage />} />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    })
  })

  it('redirects to /connect when consent already completed', async () => {
    ;(consentApi.getConsent as unknown as vi.Mock).mockResolvedValue({
      onboarding_completed: true,
    })

    useAuthSpy = vi
      .spyOn(AuthContext, 'useAuth')
      .mockReturnValue({ userId: 1, setUserId: vi.fn(), isAuthenticated: true })

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route path="/consent" element={<ConsentPage />} />
          <Route path="/connect" element={<div>Connect Page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Connect Page')).toBeInTheDocument()
    })
  })

  it('disables submit button until all four checkboxes are checked', async () => {
    ;(consentApi.getConsent as unknown as vi.Mock).mockResolvedValue(null)

    useAuthSpy = vi
      .spyOn(AuthContext, 'useAuth')
      .mockReturnValue({ userId: 1, setUserId: vi.fn(), isAuthenticated: true })

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route path="/consent" element={<ConsentPage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Wait for loading state to clear
    await waitFor(() => {
      expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument()
    })

    const button = screen.getByRole('button', {
      name: /I consent to connect my wearable data/i,
    })
    expect(button).toBeDisabled()

    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(4)

    for (const cb of checkboxes) {
      await user.click(cb)
    }

    expect(button).not.toBeDisabled()
  })

  it('submits consent and completes onboarding when all boxes are checked', async () => {
    ;(consentApi.getConsent as unknown as vi.Mock).mockResolvedValue(null)
    ;(consentApi.createConsent as unknown as vi.Mock).mockResolvedValue({})
    ;(consentApi.completeOnboarding as unknown as vi.Mock).mockResolvedValue({})

    useAuthSpy = vi
      .spyOn(AuthContext, 'useAuth')
      .mockReturnValue({ userId: 1, setUserId: vi.fn(), isAuthenticated: true })

    render(
      <MemoryRouter initialEntries={['/consent']}>
        <Routes>
          <Route path="/consent" element={<ConsentPage />} />
          <Route path="/connect" element={<div>Connect Page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.queryByText(/Loading.../i)).not.toBeInTheDocument()
    })

    const checkboxes = screen.getAllByRole('checkbox')
    for (const cb of checkboxes) {
      await user.click(cb)
    }

    const button = screen.getByRole('button', {
      name: /I consent to connect my wearable data/i,
    })
    await user.click(button)

    await waitFor(() => {
      expect(consentApi.createConsent).toHaveBeenCalledTimes(1)
      expect(consentApi.completeOnboarding).toHaveBeenCalledTimes(1)
      expect(screen.getByText('Connect Page')).toBeInTheDocument()
    })
  })
})


