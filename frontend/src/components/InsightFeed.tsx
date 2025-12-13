import { Insight } from "../types/Insight";

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
      {filteredInsights.map((insight) => (
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

          <div className={`mt-1 text-xs ${confidenceColor(insight.confidence)}`}>
            Confidence: {(insight.confidence * 100).toFixed(0)}%
          </div>

          {insight.evidence && Object.keys(insight.evidence).length > 0 && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-gray-500">
                Evidence
              </summary>
              <div className="mt-1 text-xs bg-gray-50 p-2 rounded">
                {insight.evidence.type && (
                  <div className="mb-2">
                    <strong>Type:</strong> {insight.evidence.type}
                    {insight.evidence.strength && (
                      <span className="ml-2 text-gray-600">({insight.evidence.strength})</span>
                    )}
                  </div>
                )}
                {insight.evidence.direction && (
                  <div className="mb-1">
                    <strong>Direction:</strong> {insight.evidence.direction}
                  </div>
                )}
                {insight.evidence.z_score !== undefined && (
                  <div className="mb-1">
                    <strong>Z-score:</strong> {insight.evidence.z_score.toFixed(2)}
                  </div>
                )}
                {insight.evidence.slope_per_day !== undefined && (
                  <div className="mb-1">
                    <strong>Slope:</strong> {insight.evidence.slope_per_day.toFixed(2)} per day
                  </div>
                )}
                {insight.evidence.instability_ratio !== undefined && (
                  <div className="mb-1">
                    <strong>Instability ratio:</strong> {insight.evidence.instability_ratio.toFixed(2)}x
                  </div>
                )}
                {insight.evidence.recent_mean !== undefined && insight.evidence.baseline_mean !== undefined && (
                  <div className="mb-1">
                    <strong>Recent mean:</strong> {insight.evidence.recent_mean.toFixed(2)} vs Baseline: {insight.evidence.baseline_mean.toFixed(2)}
                  </div>
                )}
                <details className="mt-2">
                  <summary className="cursor-pointer text-gray-500">Full evidence (JSON)</summary>
                  <pre className="mt-1 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                    {JSON.stringify(insight.evidence, null, 2)}
                  </pre>
                </details>
              </div>
            </details>
          )}

          {(insight as any).explanation && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-gray-500">
                Explanation
              </summary>
              <p className="mt-1 text-sm text-gray-700">
                {(insight as any).explanation}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                Uncertainty: {(insight as any).uncertainty}
              </p>
              {(insight as any).suggested_next_step && (
                <p className="mt-1 text-xs text-gray-500">
                  Next step: {(insight as any).suggested_next_step}
                </p>
              )}
            </details>
          )}

          <div className="mt-2 text-xs text-gray-400">
            {new Date(insight.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

