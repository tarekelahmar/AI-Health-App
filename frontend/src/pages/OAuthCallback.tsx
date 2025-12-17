/**
 * ALPHA WIRING: Handle OAuth callback redirects
 * This page handles the redirect from WHOOP OAuth
 */
import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function OAuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    // Check if this is a successful connection
    const connected = searchParams.get('connected');
    if (connected) {
      // Redirect to insights after successful connection
      navigate('/insights');
    } else {
      // If no connection param, just go to insights
      navigate('/insights');
    }
  }, [navigate, searchParams]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-gray-600">Connecting...</div>
    </div>
  );
}

