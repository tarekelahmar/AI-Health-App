import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Insight } from "../types/Insight";
import { fetchInsightsFeed } from "../api/insights";
import { InsightFeed } from "../components/InsightFeed";

const USER_ID = 1;

export default function InsightsPage() {
  const navigate = useNavigate();
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const feed = await fetchInsightsFeed(USER_ID);
        setInsights(feed.items || []);
      } catch (error) {
        console.error("Failed to load insights", error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-md mx-auto p-4">
        <div className="flex items-center gap-4 mb-4">
          <button onClick={() => navigate("/dashboard")} className="text-gray-600">
            ← Back
          </button>
          <h1 className="text-xl font-semibold text-gray-900">Insights</h1>
        </div>

        {loading ? (
          <div className="text-center text-gray-500">Loading...</div>
        ) : (
          <InsightFeed insights={insights} />
        )}
      </div>
    </div>
  );
}

