import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { ProgressBar } from '../components/ui/ProgressBar';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { SectionHeader } from '../components/ui/SectionHeader';
import apiClient from '../api/client';

interface CausalMemory {
  id: number;
  driver_type: string;
  driver_key: string;
  metric_key: string;
  direction: string;
  avg_effect_size: number;
  confidence: number;
  evidence_count: number;
  status: string;
  first_seen_at: string;
  last_confirmed_at?: string;
}

const statusVariant: Record<string, 'success' | 'info' | 'warning' | 'neutral'> = {
  confirmed: 'success',
  tentative: 'info',
  deprecated: 'neutral',
};

export default function MemoryPage() {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [memories, setMemories] = useState<CausalMemory[]>([]);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }
    loadMemories();
  }, [userId]);

  const loadMemories = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/memory', { params: { limit: 200 } });
      setMemories(res.data.items || []);
    } catch (error) {
      console.error('Failed to load memories', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner label="Loading personal patterns..." />;
  }

  // Group memories: helps vs doesn't help vs still learning
  const helps = memories.filter(
    (m) => m.direction === 'positive' && (m.status === 'confirmed' || m.confidence > 0.7)
  );
  const doesntHelp = memories.filter(
    (m) => m.direction === 'negative' || (m.direction === 'positive' && m.status === 'deprecated')
  );
  const learning = memories.filter(
    (m) => m.status === 'tentative' && m.confidence <= 0.7 && m.direction !== 'negative'
  );

  if (memories.length === 0) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Memory & Patterns</h1>
          <p className="text-sm text-gray-500 mt-0.5">What the system has learned about you</p>
        </div>
        <EmptyState
          title="No patterns learned yet"
          message="As you run experiments and accumulate data, the system will remember what works for your body."
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} style={{ width: 48, height: 48 }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
            </svg>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Memory & Patterns</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {memories.length} learned patterns from your personal data
        </p>
      </div>

      {/* What helps you */}
      {helps.length > 0 && (
        <Card>
          <SectionHeader title="What helps you" subtitle={`${helps.length} confirmed`} />
          <div className="space-y-3">
            {helps.map((m) => (
              <MemoryItem key={m.id} memory={m} />
            ))}
          </div>
        </Card>
      )}

      {/* What doesn't help */}
      {doesntHelp.length > 0 && (
        <Card>
          <SectionHeader title="What doesn't help" subtitle={`${doesntHelp.length} patterns`} />
          <div className="space-y-3">
            {doesntHelp.map((m) => (
              <MemoryItem key={m.id} memory={m} />
            ))}
          </div>
        </Card>
      )}

      {/* Still learning */}
      {learning.length > 0 && (
        <Card>
          <SectionHeader title="Still learning" subtitle={`${learning.length} tentative`} />
          <div className="space-y-3">
            {learning.map((m) => (
              <MemoryItem key={m.id} memory={m} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function MemoryItem({ memory }: { memory: CausalMemory }) {
  const directionIcon = memory.direction === 'positive' ? '\u2191' : '\u2193';
  const directionColor = memory.direction === 'positive' ? 'text-emerald-600' : 'text-red-500';

  return (
    <div className="flex items-start gap-3">
      <div className={`text-sm font-bold mt-0.5 ${directionColor}`}>{directionIcon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">
            {memory.driver_key.replace(/_/g, ' ')}
          </span>
          <span className="text-xs text-gray-400">&rarr;</span>
          <span className="text-sm text-gray-600">
            {memory.metric_key.replace(/_/g, ' ')}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-1">
            <ProgressBar
              value={Math.round(memory.confidence * 100)}
              max={100}
              size="sm"
              variant={memory.confidence > 0.7 ? 'success' : 'default'}
            />
          </div>
          <span className="text-[10px] text-gray-400 whitespace-nowrap">
            {Math.round(memory.confidence * 100)}% conf
          </span>
          <Badge variant={statusVariant[memory.status] || 'neutral'} size="sm">
            {memory.status}
          </Badge>
        </div>
        <div className="text-[10px] text-gray-400 mt-0.5">
          Effect: {memory.avg_effect_size.toFixed(2)} &middot;
          {memory.evidence_count} observations &middot;
          Since {new Date(memory.first_seen_at).toLocaleDateString()}
        </div>
      </div>
    </div>
  );
}
