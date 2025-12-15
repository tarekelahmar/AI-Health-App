import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createConsent, completeOnboarding } from "../api/consent";

const USER_ID = 1; // TODO: Get from auth context

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [consent, setConsent] = useState({
    understands_not_medical_advice: false,
    consents_to_data_analysis: false,
    understands_recommendations_experimental: false,
    understands_can_stop_anytime: false,
  });
  const [loading, setLoading] = useState(false);

  const handleConsentChange = (key: keyof typeof consent) => {
    setConsent((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmitConsent = async () => {
    const allChecked = Object.values(consent).every((v) => v);
    if (!allChecked) {
      alert("Please check all boxes to continue");
      return;
    }

    setLoading(true);
    try {
      await createConsent(USER_ID, consent);
      await completeOnboarding(USER_ID);
      navigate("/dashboard");
    } catch (error) {
      console.error("Failed to submit consent", error);
      alert("Failed to save consent. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-md mx-auto space-y-6">
        {/* STEP 1 — Welcome */}
        {step === 1 && (
          <div className="bg-white rounded-lg p-6 space-y-4">
            <h1 className="text-2xl font-semibold text-gray-900">
              Understand patterns in your health data
            </h1>
            <div className="space-y-3 text-gray-700">
              <p>This app analyzes your data to surface patterns.</p>
              <p>It does not provide medical advice.</p>
            </div>
            <button
              onClick={() => setStep(2)}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium"
            >
              Continue
            </button>
          </div>
        )}

        {/* STEP 2 — What this is / is not */}
        {step === 2 && (
          <div className="bg-white rounded-lg p-6 space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">What this is / is not</h2>
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
            <button
              onClick={() => setStep(3)}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium"
            >
              Continue
            </button>
          </div>
        )}

        {/* STEP 3 — Consent checklist */}
        {step === 3 && (
          <div className="bg-white rounded-lg p-6 space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Consent</h2>
            <p className="text-sm text-gray-600">Please check all boxes to continue</p>
            <div className="space-y-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consent.understands_not_medical_advice}
                  onChange={() => handleConsentChange("understands_not_medical_advice")}
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
                  onChange={() => handleConsentChange("consents_to_data_analysis")}
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
                  onChange={() => handleConsentChange("understands_recommendations_experimental")}
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
                  onChange={() => handleConsentChange("understands_can_stop_anytime")}
                  className="mt-1"
                />
                <span className="text-gray-700">
                  I can stop using this anytime
                </span>
              </label>
            </div>
            <button
              onClick={handleSubmitConsent}
              disabled={loading || !Object.values(consent).every((v) => v)}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? "Saving..." : "I agree"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

