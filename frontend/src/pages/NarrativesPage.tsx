/**
 * ALPHA WIRING: Page 5 - Narratives + Inbox
 * Combined page with tabs
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchDailyNarrative } from '../api/narratives';
import { fetchInbox } from '../api/inbox';

export default function NarrativesPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [activeTab, setActiveTab] = useState<'narratives' | 'inbox'>('narratives');
  const [narrative, setNarrative] = useState<any>(null);
  const [inboxItems, setInboxItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }

    loadData();
  }, [userId, navigate, activeTab]);

  const loadData = async () => {
    if (!userId) return;

    setLoading(true);
    try {
      if (activeTab === 'narratives') {
        const today = new Date().toISOString().split('T')[0];
        const narrativeData = await fetchDailyNarrative(userId, today).catch(() => null);
        setNarrative(narrativeData);
      } else {
        const inboxData = await fetchInbox(userId, { limit: 20, unreadOnly: false }).catch(() => ({ items: [] }));
        setInboxItems(inboxData.items || []);
      }
    } catch (error) {
      console.error('Failed to load data', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto p-4 space-y-4">
        {/* Header */}
        <div className="bg-white rounded-lg p-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">Narratives & Inbox</h1>
          <button
            onClick={() => navigate('/insights')}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Back to Insights
          </button>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg">
          <div className="flex border-b">
            <button
              onClick={() => setActiveTab('narratives')}
              className={`flex-1 py-3 px-4 text-center font-medium ${
                activeTab === 'narratives'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Narratives
            </button>
            <button
              onClick={() => setActiveTab('inbox')}
              className={`flex-1 py-3 px-4 text-center font-medium ${
                activeTab === 'inbox'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Inbox
            </button>
          </div>

          {/* Content */}
          <div className="p-4">
            {activeTab === 'narratives' ? (
              <div>
                {narrative ? (
                  <div className="space-y-3">
                    <h2 className="font-medium text-gray-900">{narrative.headline}</h2>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {narrative.summary}
                    </p>
                    {narrative.key_points && narrative.key_points.length > 0 && (
                      <div className="mt-4">
                        <h3 className="text-sm font-medium text-gray-900 mb-2">Key Points</h3>
                        <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                          {narrative.key_points.map((point: string, i: number) => (
                            <li key={i}>{point}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-600">No narrative available yet.</p>
                )}
              </div>
            ) : (
              <div>
                {inboxItems.length === 0 ? (
                  <p className="text-gray-600">No inbox items.</p>
                ) : (
                  <div className="space-y-2">
                    {inboxItems.map((item) => (
                      <div key={item.id} className="border rounded p-3">
                        <h3 className="font-medium text-gray-900">{item.title}</h3>
                        <p className="text-sm text-gray-700 mt-1">{item.body}</p>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

