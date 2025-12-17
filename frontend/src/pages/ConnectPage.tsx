/**
 * ALPHA WIRING: Page 3 - Provider Connect (WHOOP)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { whoopStatus, whoopConnect } from '../api/providers';

export default function ConnectPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }

    async function checkStatus() {
      try {
        const status = await whoopStatus(userId!);
        setConnected(status.connected);
      } catch (error) {
        console.error('Failed to check WHOOP status', error);
      } finally {
        setLoading(false);
      }
    }

    checkStatus();
  }, [userId, navigate]);

  const handleConnect = async () => {
    if (!userId) return;

    setConnecting(true);
    try {
      const response = await whoopConnect(userId);
      // Redirect to WHOOP OAuth
      window.location.href = response.authorize_url;
    } catch (error) {
      console.error('Failed to initiate WHOOP connection', error);
      alert('Failed to connect WHOOP. Please try again.');
      setConnecting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  if (connected) {
    // Already connected - redirect to insights
    navigate('/insights');
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-md mx-auto space-y-6">
        <div className="bg-white rounded-lg p-6 space-y-4">
          <h1 className="text-2xl font-semibold text-gray-900">Connect Data Source</h1>
          
          <div className="space-y-4">
            {/* WHOOP */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-gray-900">WHOOP</h3>
                <span className="text-sm text-green-600">Available</span>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Connect your WHOOP account to sync sleep, recovery, and activity data.
              </p>
              <button
                onClick={handleConnect}
                disabled={connecting}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {connecting ? 'Connecting...' : 'Connect WHOOP'}
              </button>
            </div>
          </div>

          <div className="pt-4 border-t">
            <p className="text-sm text-gray-500">
              No data sources connected yet. Connect WHOOP to get started.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

