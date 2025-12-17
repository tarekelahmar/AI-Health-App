/**
 * ALPHA WIRING: Single entry point
 * Exactly 5 routes as specified
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import ConsentPage from './pages/ConsentPage'
import ConnectPage from './pages/ConnectPage'
import InsightsFeedPage from './pages/InsightsFeedPage'
import NarrativesPage from './pages/NarrativesPage'
import OAuthCallback from './pages/OAuthCallback'
import './index.css'

function App() {
  return (
    <Routes>
      {/* ALPHA: Exactly 5 routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/consent" element={<ConsentPage />} />
      <Route path="/connect" element={<ConnectPage />} />
      <Route path="/insights" element={<InsightsFeedPage />} />
      <Route path="/narratives" element={<NarrativesPage />} />
      <Route path="/oauth/callback" element={<OAuthCallback />} />
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

