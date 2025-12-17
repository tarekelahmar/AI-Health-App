/**
 * ALPHA WIRING: Simple auth context
 * For alpha, we use AUTH_MODE=public with user_id query param
 * In production, this will use JWT tokens
 */
import React, { createContext, useContext, useState, useEffect } from 'react';

interface AuthContextType {
  userId: number | null;
  setUserId: (id: number | null) => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState<number | null>(() => {
    // For alpha: check localStorage for user_id
    const stored = localStorage.getItem('user_id');
    return stored ? parseInt(stored, 10) : null;
  });

  useEffect(() => {
    if (userId) {
      localStorage.setItem('user_id', userId.toString());
    } else {
      localStorage.removeItem('user_id');
    }
  }, [userId]);

  return (
    <AuthContext.Provider
      value={{
        userId,
        setUserId,
        isAuthenticated: userId !== null,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

