import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { whoopStatus } from "../api/providers";
import { getConsent } from "../api/consent";

const USER_ID = 1;

export default function SettingsPage() {
  const navigate = useNavigate();
  const [whoopConnected, setWhoopConnected] = useState(false);
  const [consent, setConsent] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [whoop, consentData] = await Promise.all([
          whoopStatus(USER_ID).catch(() => ({ connected: false })),
          getConsent(USER_ID).catch(() => null),
        ]);
        setWhoopConnected(whoop.connected);
        setConsent(consentData);
      } catch (error) {
        console.error("Failed to load settings", error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-md mx-auto p-4 space-y-4">
        <div className="flex items-center gap-4 mb-4">
          <button onClick={() => navigate("/dashboard")} className="text-gray-600">
            ← Back
          </button>
          <h1 className="text-xl font-semibold text-gray-900">Settings</h1>
        </div>

        {/* Connected providers */}
        <div className="bg-white rounded-lg p-4 space-y-3">
          <h2 className="font-semibold text-gray-900">Data Sources</h2>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-700">WHOOP</span>
            <span className={`text-sm ${whoopConnected ? "text-green-600" : "text-gray-400"}`}>
              {whoopConnected ? "Connected" : "Not connected"}
            </span>
          </div>
          {!whoopConnected && (
            <button
              onClick={() => navigate("/providers/whoop")}
              className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm"
            >
              Connect WHOOP
            </button>
          )}
        </div>

        {/* Consent status */}
        {consent && (
          <div className="bg-white rounded-lg p-4 space-y-2">
            <h2 className="font-semibold text-gray-900">Consent</h2>
            <div className="text-sm text-gray-700">
              <div>Version: {consent.consent_version}</div>
              <div>Date: {new Date(consent.consent_timestamp).toLocaleDateString()}</div>
              <div>Onboarding: {consent.onboarding_completed ? "Completed" : "Incomplete"}</div>
            </div>
          </div>
        )}

        {/* Data usage */}
        <div className="bg-white rounded-lg p-4 space-y-2">
          <h2 className="font-semibold text-gray-900">Data Usage</h2>
          <p className="text-sm text-gray-700">
            Your data is used to generate insights and patterns. You can export or delete your data at any time.
          </p>
        </div>

        {/* Debug: Auth mode */}
        <div className="bg-gray-100 rounded-lg p-4 space-y-2">
          <h2 className="font-semibold text-gray-900 text-xs">Debug</h2>
          <div className="text-xs text-gray-600">
            AUTH_MODE: {import.meta.env.VITE_AUTH_MODE || "public"}
          </div>
        </div>
      </div>
    </div>
  );
}

