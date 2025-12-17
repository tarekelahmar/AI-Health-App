/**
 * ALPHA WIRING: Use unified API client
 */
import apiClient from "./client";

export interface ConsentData {
  understands_not_medical_advice: boolean;
  consents_to_data_analysis: boolean;
  understands_recommendations_experimental: boolean;
  understands_can_stop_anytime: boolean;
}

export interface ConsentResponse {
  id: number;
  user_id: number;
  consent_version: string;
  consent_timestamp: string;
  understands_not_medical_advice: boolean;
  consents_to_data_analysis: boolean;
  understands_recommendations_experimental: boolean;
  understands_can_stop_anytime: boolean;
  onboarding_completed: boolean;
  onboarding_completed_at: string | null;
}

export async function getConsent(userId: number): Promise<ConsentResponse | null> {
  try {
    const res = await apiClient.get("/consent", {
      params: { user_id: userId },
    });
    return res.data;
  } catch (error: any) {
    if (error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function createConsent(userId: number, consent: ConsentData): Promise<ConsentResponse> {
  const res = await apiClient.post(
    "/consent",
    {
      consent_version: "1.0",
      ...consent,
    },
    {
      params: { user_id: userId },
    }
  );
  return res.data;
}

export async function completeOnboarding(userId: number): Promise<ConsentResponse> {
  const res = await apiClient.post(
    "/consent/complete-onboarding",
    {},
    {
      params: { user_id: userId },
    }
  );
  return res.data;
}

