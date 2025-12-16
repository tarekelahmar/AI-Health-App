/**
 * ALPHA WIRING: Unified API client
 * Single source of truth for API base URL
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with base config
const apiClient = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout to prevent hanging requests
});

// For alpha: add user_id to all requests if in public mode
apiClient.interceptors.request.use((config) => {
  const authMode = import.meta.env.VITE_AUTH_MODE || 'public';
  
  if (authMode === 'public') {
    const userId = localStorage.getItem('user_id');
    if (userId && !config.params) {
      config.params = {};
    }
    if (userId && config.params) {
      config.params.user_id = userId;
    }
  } else {
    // Private mode: add bearer token
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  
  return config;
});

// Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      localStorage.removeItem('accessToken');
      localStorage.removeItem('user_id');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
