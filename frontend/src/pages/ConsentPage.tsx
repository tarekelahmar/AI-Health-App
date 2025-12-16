/**
 * ALPHA WIRING: Page 2 - Consent
 * Mandatory consent before accessing the app
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getConsent, createConsent, completeOnboarding, ConsentData } from '../api/consent';

export default function ConsentPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [consent, setConsent] = useState<ConsentData>({
    understands_not_medical_advice: false,
    consents_to_data_analysis: false,
    understands_recommendations_experimental: false,
    understands_can_stop_anytime: false,
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [hasConsent, setHasConsent] = useState(false);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }

    async function checkConsent() {
      try {
        const existing = await getConsent(userId!);
        if (existing && existing.onboarding_completed) {
          setHasConsent(true);
          // Redirect to connect page if consent exists
          navigate('/connect');
        }
      } catch (error: any) {
        console.error('Failed to check consent', error);
        // If it's a 404, that's fine - user just needs to create consent
        // If it's a timeout or network error, still show the form
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          console.warn('Request timed out, showing consent form anyway');
        }
      } finally {
        setLoading(false);
      }
    }

    checkConsent();
  }, [userId, navigate]);

  const handleConsentChange = (key: keyof ConsentData) => {
    setConsent((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = async () => {
    const allChecked = Object.values(consent).every((v) => v);
    if (!allChecked) {
      alert('Please check all boxes to continue');
      return;
    }

    if (!userId) {
      navigate('/login');
      return;
    }

    setSubmitting(true);
    try {
      await createConsent(userId, consent);
      await completeOnboarding(userId);
      // Redirect to provider connect
      navigate('/connect');
    } catch (error: any) {
      console.error('Failed to submit consent', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
      console.error('Error details:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message,
      });
      alert(`Failed to save consent: ${errorMessage}. Please check the console for details.`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (hasConsent) {
    return null; // Will redirect
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-md mx-auto space-y-6">
        {/* What this is / is not */}
        <div className="bg-white rounded-lg p-6 space-y-4">
          <h1 className="text-2xl font-semibold text-gray-900">What this is / is not</h1>
          <div className="space-y-3 text-gray-700">
            <div className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span>Looks at trends over time</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span>Helps you test what helps you</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-red-600 font-bold">✗</span>
              <span>Does not diagnose conditions</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-red-600 font-bold">✗</span>
              <span>Does not replace clinicians</span>
            </div>
          </div>
        </div>

        {/* Consent checklist */}
        <div className="bg-white rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Consent</h2>
          <p className="text-sm text-gray-600">Please check all boxes to continue</p>
          <div className="space-y-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.understands_not_medical_advice}
                onChange={() => handleConsentChange('understands_not_medical_advice')}
                className="mt-1"
              />
              <span className="text-gray-700">
                I understand this is not medical advice
              </span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.consents_to_data_analysis}
                onChange={() => handleConsentChange('consents_to_data_analysis')}
                className="mt-1"
              />
              <span className="text-gray-700">
                I consent to analysis of my health data
              </span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.understands_recommendations_experimental}
                onChange={() => handleConsentChange('understands_recommendations_experimental')}
                className="mt-1"
              />
              <span className="text-gray-700">
                I understand recommendations are experimental
              </span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={consent.understands_can_stop_anytime}
                onChange={() => handleConsentChange('understands_can_stop_anytime')}
                className="mt-1"
              />
              <span className="text-gray-700">
                I can stop using this anytime
              </span>
            </label>
          </div>
          <button
            onClick={handleSubmit}
            disabled={submitting || !Object.values(consent).every((v) => v)}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {submitting ? 'Saving...' : 'I consent to connect my wearable data'}
          </button>
        </div>
      </div>
    </div>
  );
}

