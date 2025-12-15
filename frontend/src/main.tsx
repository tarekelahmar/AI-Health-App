import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Onboarding from './pages/Onboarding'
import InsightsPage from './pages/InsightsPage'
import MetricsPage from './pages/MetricsPage'
import SettingsPage from './pages/SettingsPage'
import { getConsent } from './api/consent'
import './index.css'

const USER_ID = 1; // TODO: Get from auth context

function App() {
  const [hasConsent, setHasConsent] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkConsent() {
      try {
        const consent = await getConsent(USER_ID);
        setHasConsent(consent !== null && consent.onboarding_completed);
      } catch (error) {
        console.error("Failed to check consent", error);
        setHasConsent(false);
      } finally {
        setLoading(false);
      }
    }
    checkConsent();
  }, []);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50">Loading...</div>;
  }

  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/insights" element={<InsightsPage />} />
      <Route path="/metrics" element={<MetricsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/" element={hasConsent ? <Navigate to="/dashboard" /> : <Navigate to="/onboarding" />} />
    </Routes>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)

