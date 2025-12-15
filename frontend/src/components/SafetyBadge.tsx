import React from "react";
import type { RiskLevel, EvidenceGrade, BoundaryCategory, SafetyDecision } from "../types/Safety";

function pillClass(base: string) {
  return `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${base}`;
}

function riskPill(risk: RiskLevel) {
  if (risk === "high") return pillClass("bg-red-100 text-red-800");
  if (risk === "moderate") return pillClass("bg-yellow-100 text-yellow-800");
  return pillClass("bg-green-100 text-green-800");
}

function evidencePill(g: EvidenceGrade) {
  if (g === "A") return pillClass("bg-green-100 text-green-800");
  if (g === "B") return pillClass("bg-emerald-100 text-emerald-800");
  if (g === "C") return pillClass("bg-yellow-100 text-yellow-800");
  return pillClass("bg-gray-100 text-gray-800");
}

function boundaryPill(b: BoundaryCategory) {
  if (b === "informational") return pillClass("bg-blue-100 text-blue-800");
  if (b === "lifestyle") return pillClass("bg-indigo-100 text-indigo-800");
  return pillClass("bg-purple-100 text-purple-800");
}

export function SafetyBadge({ safety }: { safety?: Partial<SafetyDecision> }) {
  if (!safety) return null;

  const risk = (safety.risk || "moderate") as RiskLevel;
  const boundary = (safety.boundary || "experiment") as BoundaryCategory;
  const evidence = (safety.evidence_grade || "D") as EvidenceGrade;

  return (
    <div className="flex flex-wrap gap-2">
      <span className={riskPill(risk)}>Risk: {risk}</span>
      <span className={evidencePill(evidence)}>Evidence: {evidence}</span>
      <span className={boundaryPill(boundary)}>Mode: {boundary}</span>
    </div>
  );
}

export function SafetyDetails({ safety }: { safety?: Partial<SafetyDecision> }) {
  if (!safety) return null;

  const issues = safety.issues || [];
  if (!issues.length) return null;

  return (
    <div className="mt-2 rounded-lg border border-gray-200 bg-white p-3">
      <div className="text-sm font-semibold text-gray-900">Safety notes</div>
      <ul className="mt-2 space-y-2">
        {issues.map((i, idx) => (
          <li key={idx} className="text-sm text-gray-700">
            <span className="font-medium">{i.code}</span>: {i.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

