import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { AppShell } from './components/layout/AppShell'
import LoginPage from './pages/LoginPage'
import ConsentPage from './pages/ConsentPage'
import ConnectPage from './pages/ConnectPage'
import OAuthCallback from './pages/OAuthCallback'
import DashboardPage from './pages/DashboardPage'
import DomainsPage from './pages/DomainsPage'
import DomainDetailPage from './pages/DomainDetailPage'
import ForecastsPage from './pages/ForecastsPage'
import ExperimentsPage from './pages/ExperimentsPage'
import MemoryPage from './pages/MemoryPage'
import JournalPage from './pages/JournalPage'
import InsightsFeedPage from './pages/InsightsFeedPage'
import NarrativesPage from './pages/NarrativesPage'
import SettingsPage from './pages/SettingsPage'
import ActionDetailPage from './pages/ActionDetailPage'
import './index.css'

function App() {
  return (
    <Routes>
      {/* Onboarding routes (no navigation shell) */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/consent" element={<ConsentPage />} />
      <Route path="/connect" element={<ConnectPage />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />

      {/* Authenticated routes (with AppShell navigation) */}
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/domains" element={<DomainsPage />} />
        <Route path="/domains/:key" element={<DomainDetailPage />} />
        <Route path="/forecasts" element={<ForecastsPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/journal" element={<JournalPage />} />
        <Route path="/memory" element={<MemoryPage />} />
        <Route path="/insights" element={<InsightsFeedPage />} />
        <Route path="/narratives" element={<NarrativesPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/actions/:id" element={<ActionDetailPage />} />
      </Route>

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
