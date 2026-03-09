import { Insight } from "../types/Insight";
import { InteractionSummary } from "./InteractionSummary";
import { SafetyBadge, SafetyDetails } from "./SafetyBadge";
import { DomainMeta } from "./DomainMeta";

function SafetyTriggers({ triggers }: { triggers: any[] }) {
  return (
    <div className="mt-2 space-y-2">
      {triggers.map((t, idx) => (
        <div key={idx} className="rounded border border-red-300 bg-red-50 p-2 text-sm">
          <div className="font-semibold">
            {t.severity.toUpperCase()} — {t.action.replaceAll("_", " ")}
          </div>
          <div className="mt-1">{t.message}</div>
          {t.evidence?.value !== undefined && (
            <div className="mt-1 text-gray-700">
              Value: <b>{String(t.evidence.value)}</b>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

type Props = {
  insights: Insight[];
  filterByMetric?: string;
};

function confidenceColor(confidence: number) {
  if (confidence >= 0.8) return "text-green-600";
  if (confidence >= 0.5) return "text-yellow-600";
  return "text-red-600";
}

function getInsightTypeBadge(evidence: any) {
  const type = evidence?.type;
  if (!type) return null;
  
  const colors: Record<string, string> = {
    change: "bg-blue-100 text-blue-800",
    trend: "bg-purple-100 text-purple-800",
    instability: "bg-orange-100 text-orange-800",
  };
  
  return (
    <span className={`text-xs px-2 py-1 rounded ${colors[type] || "bg-gray-100"}`}>
      {type}
    </span>
  );
}

export function InsightFeed({ insights, filterByMetric }: Props) {
  // Filter insights by metric if specified
  const filteredInsights = filterByMetric
    ? insights.filter((i) => i.metric_key === filterByMetric)
    : insights;

  if (filteredInsights.length === 0) {
    return (
      <div className="text-gray-500 text-sm">
        {filterByMetric ? `No insights for ${filterByMetric} yet.` : "No insights yet."}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600 mb-2">
        {filterByMetric ? (
          <>Showing {filteredInsights.length} insight{filteredInsights.length !== 1 ? "s" : ""} for <strong>{filterByMetric}</strong></>
        ) : (
          <>Showing {filteredInsights.length} insight{filteredInsights.length !== 1 ? "s" : ""}</>
        )}
      </div>
      {filteredInsights.map((insight) => {
        const evidence: any = insight.evidence;
        if (evidence?.type === "safety" && evidence?.triggers) {
          return (
            <div
              key={insight.id}
              className="border-2 border-red-500 rounded-lg p-4 bg-red-50 shadow-sm"
            >
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-red-800">{insight.title}</h3>
                <span className="text-xs px-2 py-1 rounded bg-red-200 text-red-800 font-semibold">
                  SAFETY ALERT
                </span>
              </div>
              <p className="text-sm text-gray-800 mt-1">
                {insight.summary}
              </p>
              <SafetyTriggers triggers={evidence.triggers} />
              <div className="mt-2 text-xs text-gray-500">
                {new Date(insight.created_at).toLocaleString()}
              </div>
            </div>
          );
        }

        return (
          <div
            key={insight.id}
            className="border rounded-lg p-4 bg-white shadow-sm"
          >
            <div className="flex justify-between items-center">
              <h3 className="font-semibold">{insight.title}</h3>
              <div className="flex gap-2 items-center">
                {getInsightTypeBadge(insight.evidence)}
                <span className="text-xs px-2 py-1 rounded bg-gray-100">
                  {insight.status}
                </span>
              </div>
            </div>

            <p className="text-sm text-gray-700 mt-1">
              {insight.summary}
            </p>

            <div className="mt-2 text-xs text-gray-600">
              Metric: <strong>{insight.metric_key}</strong>
            </div>

            {/* Domain label (read-only metadata). Explanation is only shown if domain info is provided elsewhere. */}
            <DomainMeta domainKey={insight.domain_key} />

            {/* STEP S: Always show confidence and uncertainty */}
            <div className={`mt-2 text-xs ${confidenceColor(insight.confidence)}`}>
              Confidence: {(insight.confidence * 100).toFixed(0)}%
            </div>
            
            {/* Uncertainty message (always visible) */}
            <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
              {insight.confidence < 0.5 ? (
                <span className="text-orange-600">⚠️ This insight is based on limited data</span>
              ) : insight.confidence < 0.8 ? (
                <span>Moderate confidence based on available data</span>
              ) : (
                <span className="text-green-600">✓ High confidence based on sufficient data</span>
              )}
            </div>

            {insight.evidence?.interaction && (
              <InteractionSummary
                confounder={insight.evidence.interaction.confounder_key || "confounder"}
                message={insight.evidence.interaction.message || insight.evidence.interaction.note || "Interaction detected"}
              />
            )}

            {/* Safety metadata (optional) */}
            {insight.evidence?.safety && (
              <div className="mt-2">
                <SafetyBadge safety={insight.evidence.safety as any} />
                <SafetyDetails safety={insight.evidence.safety as any} />
              </div>
            )}

            {/* Human-readable explanation (primary display) */}
            {insight.explanation && (
              <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-2">
                <p className="text-sm text-gray-700 leading-relaxed">
                  {insight.explanation}
                </p>

                {insight.uncertainty && (
                  <div className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-100 p-2 rounded-md">
                    <span className="shrink-0 mt-0.5 text-amber-500">ℹ</span>
                    <span>{insight.uncertainty}</span>
                  </div>
                )}

                {insight.suggested_next_step && (
                  <div className="flex items-start gap-2 text-xs text-gray-700 bg-teal-50 border border-teal-100 p-2 rounded-md">
                    <span className="shrink-0 mt-0.5 text-teal-600">→</span>
                    <span><span className="font-medium">Next step:</span> {insight.suggested_next_step}</span>
                  </div>
                )}
              </div>
            )}

            {/* Raw evidence — developer/advanced toggle */}
            {insight.evidence && Object.keys(insight.evidence).length > 0 && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-500">
                  View raw evidence data
                </summary>
                <pre className="mt-1 text-xs bg-gray-100 p-2 rounded overflow-x-auto text-gray-500">
                  {JSON.stringify(insight.evidence, null, 2)}
                </pre>
              </details>
            )}

            <div className="mt-2 text-xs text-gray-400">
              {new Date(insight.created_at).toLocaleString()}
            </div>
          </div>
        );
      })}
    </div>
  );
}

