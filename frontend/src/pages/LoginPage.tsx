/**
 * ALPHA WIRING: Page 1 - Login
 * Simple login for alpha - just sets user_id
 * In production, this will use proper JWT auth
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const navigate = useNavigate();
  const { setUserId } = useAuth();
  const [userIdInput, setUserIdInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const userId = parseInt(userIdInput, 10);
    if (isNaN(userId) || userId <= 0) {
      alert('Please enter a valid user ID');
      return;
    }

    setLoading(true);
    try {
      // For alpha: just set user_id
      // In production, this would call /api/v1/auth/login and get a token
      setUserId(userId);
      
      // Redirect to consent check
      navigate('/consent');
    } catch (error) {
      console.error('Login failed', error);
      alert('Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-sm p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Sign in</h1>
          <p className="mt-2 text-sm text-gray-600">
            Enter your user ID to continue
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="userId" className="block text-sm font-medium text-gray-700">
              User ID
            </label>
            <input
              id="userId"
              type="number"
              value={userIdInput}
              onChange={(e) => setUserIdInput(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              placeholder="Enter user ID"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-xs text-gray-500 text-center">
          Alpha: This is a simplified login. Production will use secure authentication.
        </p>
      </div>
    </div>
  );
}

