export type RiskLevel = "low" | "moderate" | "high";
export type EvidenceGrade = "A" | "B" | "C" | "D";
export type BoundaryCategory = "informational" | "lifestyle" | "experiment";

export interface SafetyIssue {
  code: string;
  severity: RiskLevel;
  message: string;
  details?: Record<string, any>;
}

export interface SafetyDecision {
  allowed: boolean;
  risk: RiskLevel;
  boundary: BoundaryCategory;
  evidence_grade: EvidenceGrade;
  issues: SafetyIssue[];
}

export interface SafetyEvaluateRequest {
  intervention_key: string;
  user_flags?: Record<string, any>;
  requested_boundary?: string;
  requested_evidence?: string;
}

