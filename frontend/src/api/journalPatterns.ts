import apiClient from './client';
import type {
  FactorExtractionResponse,
  JournalPatternData,
  PatternComputeResult,
} from '../types/JournalFactors';
import type { CompanionAnalyzeResponse } from '../types/CompanionResponse';

export async function extractFactors(text: string): Promise<FactorExtractionResponse> {
  const res = await apiClient.post('/journal/extract-factors', { text });
  return res.data;
}

export async function analyzeWithCompanion(
  checkinId: number,
  depthLevel: number = 2,
): Promise<CompanionAnalyzeResponse> {
  const res = await apiClient.post('/journal/companion/analyze', {
    checkin_id: checkinId,
    depth_level: depthLevel,
  });
  return res.data;
}

export async function getJournalPatterns(): Promise<JournalPatternData[]> {
  const res = await apiClient.get('/journal/patterns');
  return res.data;
}

export async function computePatterns(): Promise<PatternComputeResult> {
  const res = await apiClient.post('/journal/patterns/compute');
  return res.data;
}
