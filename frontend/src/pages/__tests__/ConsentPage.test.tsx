/**
 * ConsentPage Tests
 *
 * Tests the critical consent flow that users must complete before
 * accessing the app. All 4 checkboxes must be checked for the
 * submit button to be enabled.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import ConsentPage from '../ConsentPage'
import * as consentApi from '../../api/consent'
import * as AuthContext from '../../contexts/AuthContext'

// Mock the API module
vi.mock('../../api/consent', () => ({
  getConsent: vi.fn(),
  createConsent: vi.fn(),
  completeOnboarding: vi.fn(),
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Helper to render with router context
function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

describe('ConsentPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: user is logged in with userId 1
    vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
      userId: 1,
      setUserId: vi.fn(),
      isAuthenticated: true,
    })
    // Default: no existing consent
    vi.mocked(consentApi.getConsent).mockResolvedValue(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Loading State', () => {
    it('shows loading state initially', () => {
      // Make getConsent hang to keep loading state
      vi.mocked(consentApi.getConsent).mockImplementation(
        () => new Promise(() => {})
      )
      renderWithRouter(<ConsentPage />)
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })
  })

  describe('Authentication Check', () => {
    it('redirects to login if no userId', () => {
      vi.spyOn(AuthContext, 'useAuth').mockReturnValue({
        userId: null,
        setUserId: vi.fn(),
        isAuthenticated: false,
      })
      renderWithRouter(<ConsentPage />)
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  describe('Existing Consent', () => {
    it('redirects to connect if consent already completed', async () => {
      vi.mocked(consentApi.getConsent).mockResolvedValue({
        id: 1,
        user_id: 1,
        consent_version: '1.0',
        consent_timestamp: '2024-01-01T00:00:00Z',
        understands_not_medical_advice: true,
        consents_to_data_analysis: true,
        understands_recommendations_experimental: true,
        understands_can_stop_anytime: true,
        onboarding_completed: true,
        onboarding_completed_at: '2024-01-01T00:00:00Z',
      })
      renderWithRouter(<ConsentPage />)

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/connect')
      })
    })
  })

  describe('Consent Form Display', () => {
    it('displays the what this is/is not section', async () => {
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.getByText('What this is / is not')).toBeInTheDocument()
      })
    })

    it('displays positive aspects', async () => {
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.getByText('Looks at trends over time')).toBeInTheDocument()
        expect(screen.getByText('Helps you test what helps you')).toBeInTheDocument()
      })
    })

    it('displays negative aspects (what this is NOT)', async () => {
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.getByText('Does not diagnose conditions')).toBeInTheDocument()
        expect(screen.getByText('Does not replace clinicians')).toBeInTheDocument()
      })
    })

    it('displays all 4 consent checkboxes', async () => {
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(
          screen.getByText('I understand this is not medical advice')
        ).toBeInTheDocument()
        expect(
          screen.getByText('I consent to analysis of my health data')
        ).toBeInTheDocument()
        expect(
          screen.getByText('I understand recommendations are experimental')
        ).toBeInTheDocument()
        expect(screen.getByText('I can stop using this anytime')).toBeInTheDocument()
      })
    })
  })

  describe('Checkbox Interactions', () => {
    it('checkboxes start unchecked', async () => {
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes).toHaveLength(4)
      checkboxes.forEach((cb) => {
        expect(cb).not.toBeChecked()
      })
    })

    it('can check individual checkboxes', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0])

      expect(checkboxes[0]).toBeChecked()
      expect(checkboxes[1]).not.toBeChecked()
      expect(checkboxes[2]).not.toBeChecked()
      expect(checkboxes[3]).not.toBeChecked()
    })
  })

  describe('Submit Button State', () => {
    it('submit button is disabled when no checkboxes checked', async () => {
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const button = screen.getByRole('button', {
        name: /I consent to connect my wearable data/i,
      })
      expect(button).toBeDisabled()
    })

    it('submit button is disabled when only some checkboxes checked', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0])
      await user.click(checkboxes[1])

      const button = screen.getByRole('button', {
        name: /I consent to connect my wearable data/i,
      })
      expect(button).toBeDisabled()
    })

    it('submit button is enabled when all 4 checkboxes checked', async () => {
      const user = userEvent.setup()
      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const checkboxes = screen.getAllByRole('checkbox')
      for (const cb of checkboxes) {
        await user.click(cb)
      }

      const button = screen.getByRole('button', {
        name: /I consent to connect my wearable data/i,
      })
      expect(button).not.toBeDisabled()
    })
  })

  describe('Form Submission', () => {
    it('calls createConsent and completeOnboarding on submit', async () => {
      const user = userEvent.setup()
      vi.mocked(consentApi.createConsent).mockResolvedValue({
        id: 1,
        user_id: 1,
        consent_version: '1.0',
        consent_timestamp: '2024-01-01T00:00:00Z',
        understands_not_medical_advice: true,
        consents_to_data_analysis: true,
        understands_recommendations_experimental: true,
        understands_can_stop_anytime: true,
        onboarding_completed: false,
        onboarding_completed_at: null,
      })
      vi.mocked(consentApi.completeOnboarding).mockResolvedValue({
        id: 1,
        user_id: 1,
        consent_version: '1.0',
        consent_timestamp: '2024-01-01T00:00:00Z',
        understands_not_medical_advice: true,
        consents_to_data_analysis: true,
        understands_recommendations_experimental: true,
        understands_can_stop_anytime: true,
        onboarding_completed: true,
        onboarding_completed_at: '2024-01-01T00:00:00Z',
      })

      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Check all boxes
      const checkboxes = screen.getAllByRole('checkbox')
      for (const cb of checkboxes) {
        await user.click(cb)
      }

      // Click submit
      const button = screen.getByRole('button', {
        name: /I consent to connect my wearable data/i,
      })
      await user.click(button)

      await waitFor(() => {
        expect(consentApi.createConsent).toHaveBeenCalledWith(1, {
          understands_not_medical_advice: true,
          consents_to_data_analysis: true,
          understands_recommendations_experimental: true,
          understands_can_stop_anytime: true,
        })
        expect(consentApi.completeOnboarding).toHaveBeenCalledWith(1)
      })
    })

    it('redirects to /connect after successful submission', async () => {
      const user = userEvent.setup()
      vi.mocked(consentApi.createConsent).mockResolvedValue({
        id: 1,
        user_id: 1,
        consent_version: '1.0',
        consent_timestamp: '2024-01-01T00:00:00Z',
        understands_not_medical_advice: true,
        consents_to_data_analysis: true,
        understands_recommendations_experimental: true,
        understands_can_stop_anytime: true,
        onboarding_completed: false,
        onboarding_completed_at: null,
      })
      vi.mocked(consentApi.completeOnboarding).mockResolvedValue({
        id: 1,
        user_id: 1,
        consent_version: '1.0',
        consent_timestamp: '2024-01-01T00:00:00Z',
        understands_not_medical_advice: true,
        consents_to_data_analysis: true,
        understands_recommendations_experimental: true,
        understands_can_stop_anytime: true,
        onboarding_completed: true,
        onboarding_completed_at: '2024-01-01T00:00:00Z',
      })

      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Check all boxes
      const checkboxes = screen.getAllByRole('checkbox')
      for (const cb of checkboxes) {
        await user.click(cb)
      }

      // Click submit
      const button = screen.getByRole('button', {
        name: /I consent to connect my wearable data/i,
      })
      await user.click(button)

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/connect')
      })
    })

    it('shows Saving... text while submitting', async () => {
      const user = userEvent.setup()
      // Make createConsent hang
      vi.mocked(consentApi.createConsent).mockImplementation(
        () => new Promise(() => {})
      )

      renderWithRouter(<ConsentPage />)
      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Check all boxes
      const checkboxes = screen.getAllByRole('checkbox')
      for (const cb of checkboxes) {
        await user.click(cb)
      }

      // Click submit
      const button = screen.getByRole('button', {
        name: /I consent to connect my wearable data/i,
      })
      await user.click(button)

      await waitFor(() => {
        expect(screen.getByText('Saving...')).toBeInTheDocument()
      })
    })
  })
})
