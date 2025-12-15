import React from "react";
import { ConfidenceBreakdown } from "../types/Confidence";

interface Props {
  c: ConfidenceBreakdown;
}

export function ConfidenceBar({ c }: Props) {
  const color =
    c.level === "high"
      ? "bg-green-500"
      : c.level === "medium"
      ? "bg-yellow-500"
      : "bg-red-500";

  const percentage = Math.round(c.score * 100);

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>Confidence</span>
        <span className="capitalize font-medium">{c.level}</span>
      </div>

      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="flex justify-between items-center text-xs text-gray-600">
        <span>Based on {c.data_coverage_days} days of data</span>
        <span>{percentage}%</span>
      </div>

      {c.uncertainty_reasons.length > 0 && (
        <div className="text-xs text-gray-500 mt-1">
          <span className="font-medium">Uncertainty factors: </span>
          {c.uncertainty_reasons
            .map((r) => r.replace(/_/g, " "))
            .join(", ")}
        </div>
      )}

      {c.effect_size !== undefined && (
        <div className="text-xs text-gray-500">
          Effect size: {c.effect_size.toFixed(2)}
        </div>
      )}
    </div>
  );
}

