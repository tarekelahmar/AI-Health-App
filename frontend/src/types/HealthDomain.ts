export interface HealthDomainInfo {
  key: string; // e.g. "sleep"
  display_name: string; // e.g. "Sleep"
  description: string; // short neutral description (non-diagnostic, non-prescriptive)
  example_signals: string[];
}

export interface HealthDomainsResponse {
  count: number;
  items: HealthDomainInfo[];
}


