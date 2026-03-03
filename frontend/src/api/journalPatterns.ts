import apiClient from './client';
import type {
  FactorExtractionResponse,
  JournalPatternData,
  PatternComputeResult,
} from '../types/JournalFactors';

export async function extractFactors(text: string): Promise<FactorExtractionResponse> {
  const res = await apiClient.post('/journal/extract-factors', { text });
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
