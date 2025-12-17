import apiClient from "./client";
import { HealthDomainsResponse, HealthDomainInfo } from "../types/HealthDomain";

export async function fetchHealthDomains(): Promise<HealthDomainsResponse> {
  const res = await apiClient.get("/health-domains");
  return res.data;
}

export async function fetchHealthDomain(domainKey: string): Promise<HealthDomainInfo> {
  const res = await apiClient.get(`/health-domains/${domainKey}`);
  return res.data;
}


