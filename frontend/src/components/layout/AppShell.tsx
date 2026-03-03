import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { BottomNav } from './BottomNav';

interface AppShellProps {
  regimeLabel?: string;
  regimeVariant?: 'normal' | 'stress' | 'illness' | 'travel';
}

const regimeColors: Record<string, string> = {
  stress: 'bg-amber-50 text-amber-800 border-amber-200',
  illness: 'bg-red-50 text-red-800 border-red-200',
  travel: 'bg-amber-50 text-amber-800 border-amber-200',
};

export function AppShell({ regimeLabel, regimeVariant }: AppShellProps) {
  const showRegime = regimeVariant && regimeVariant !== 'normal' && regimeLabel;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Top bar */}
      <header className="sticky top-0 z-40 bg-white border-b border-gray-100">
        <div className="flex items-center justify-between h-14 px-4 max-w-lg mx-auto">
          <Link to="/dashboard" className="text-lg font-bold text-primary-700 tracking-tight">
            Health OS
          </Link>
          <Link
            to="/settings"
            className="p-2 -mr-2 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Settings"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Link>
        </div>
        {showRegime && (
          <div className={`px-4 py-1.5 text-xs font-medium text-center border-t ${regimeColors[regimeVariant] || ''}`}>
            {regimeLabel}
          </div>
        )}
      </header>

      {/* Page content with bottom padding for nav */}
      <main className="flex-1 px-4 pt-4 pb-24 max-w-lg mx-auto w-full">
        <Outlet />
      </main>

      {/* Bottom navigation */}
      <BottomNav />
    </div>
  );
}
