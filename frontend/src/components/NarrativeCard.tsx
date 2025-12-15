import React from "react";
import type { NarrativeResponse } from "../types/Narrative";

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function NarrativeCard({ narrative }: { narrative: NarrativeResponse | null }) {
  if (!narrative) {
    return (
      <div className="rounded-2xl bg-white border p-4">
        <div className="text-sm text-gray-500">No narrative yet.</div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-white border p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-lg font-semibold">{narrative.title}</div>
          <div className="text-xs text-gray-500">
            Generated {fmtDate(narrative.created_at)} • {narrative.period_type}
          </div>
        </div>
        <div className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">
          {narrative.metadata?.insights_count ?? 0} insights
        </div>
      </div>

      <div className="text-sm text-gray-700">{narrative.summary}</div>

      {Array.isArray(narrative.key_points) && narrative.key_points.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wide text-gray-500">Key points</div>
          <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
            {narrative.key_points.slice(0, 5).map((kp, idx) => (
              <li key={idx}>{typeof kp === "string" ? kp : JSON.stringify(kp)}</li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(narrative.actions) && narrative.actions.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wide text-gray-500 font-medium">What seems to be helping</div>
          <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
            {narrative.actions.slice(0, 4).map((a, idx) => (
              <li key={idx}>
                <span className="font-medium">{a.action ?? "Action"}:</span>{" "}
                <span className="text-gray-600">{a.rationale ?? ""}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* STEP S: Show "What's unclear" if there are actions with unclear verdicts */}
      {Array.isArray(narrative.actions) && narrative.actions.some((a: any) => a.rationale?.includes("unclear") || a.rationale?.includes("review")) && (
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wide text-gray-500 font-medium">What's unclear</div>
          <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
            {narrative.actions
              .filter((a: any) => a.rationale?.includes("unclear") || a.rationale?.includes("review"))
              .slice(0, 3)
              .map((a, idx) => (
                <li key={idx}>
                  <span className="font-medium">{a.action ?? "Action"}:</span>{" "}
                  <span className="text-gray-600">{a.rationale ?? ""}</span>
                </li>
              ))}
          </ul>
        </div>
      )}

      {Array.isArray(narrative.risks) && narrative.risks.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wide text-red-600 font-medium">Any risks</div>
          <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
            {narrative.risks.slice(0, 3).map((r, idx) => (
              <li key={idx}>
                <span className="font-medium text-red-700">{r.risk ?? "Note"}:</span>{" "}
                <span className="text-gray-600">{r.guidance ?? ""}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

