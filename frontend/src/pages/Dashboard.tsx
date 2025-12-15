import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Insight } from "../types/Insight";
import { fetchInsightsFeed } from "../api/insights";
import { fetchDailyNarrative } from "../api/narratives";
import { fetchInboxItems } from "../api/inbox";
import NarrativeCard from "../components/NarrativeCard";
import InboxPanel from "../components/InboxPanel";
import DailyCheckIn from "../components/DailyCheckIn";
import { InsightFeed } from "../components/InsightFeed";
import DriversPanel from "../components/DriversPanel";
import PersonalDriversPanel from "../components/PersonalDriversPanel";
import { fetchRecentDrivers, generateDrivers } from "../api/drivers";
import { fetchPersonalDrivers, recomputePersonalDrivers } from "../api/personalDrivers";
import type { DriverFinding } from "../types/Drivers";
import type { PersonalDriver } from "../types/PersonalDrivers";

const USER_ID = 1; // TODO: Get from auth context

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [dailyNarrative, setDailyNarrative] = useState<any>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [inboxItems, setInboxItems] = useState<any[]>([]);
  const [driverFindings, setDriverFindings] = useState<DriverFinding[]>([]);
  const [personalDrivers, setPersonalDrivers] = useState<PersonalDriver[]>([]);
  const [loading, setLoading] = useState(false);
  const [driverLoading, setDriverLoading] = useState(false);
  const [personalDriverLoading, setPersonalDriverLoading] = useState(false);
  const [showCheckIn, setShowCheckIn] = useState(false);

  async function loadAll() {
    setLoading(true);
    try {
      const [narrative, feed, inbox, drivers, personal] = await Promise.all([
        fetchDailyNarrative(USER_ID, todayISO()).catch(() => null),
        fetchInsightsFeed(USER_ID).catch(() => ({ items: [] })),
        fetchInbox(USER_ID, { limit: 10, unreadOnly: false }).catch(() => ({ items: [] })),
        fetchRecentDrivers(USER_ID, 20).catch(() => ({ items: [] })),
        fetchPersonalDrivers(USER_ID, 50).catch(() => ({ items: [] })),
      ]);
      setDailyNarrative(narrative);
      setInsights(feed.items || []);
      setInboxItems(inbox.items || []);
      setDriverFindings(drivers.items || []);
      setPersonalDrivers(personal.items || []);
    } catch (error) {
      console.error("Failed to load dashboard", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefreshDrivers() {
    setDriverLoading(true);
    try {
      await generateDrivers(USER_ID, 28);
      const drivers = await fetchRecentDrivers(USER_ID, 20);
      setDriverFindings(drivers.items || []);
    } catch (error) {
      console.error("Failed to refresh drivers", error);
      alert("Failed to refresh drivers. Please try again.");
    } finally {
      setDriverLoading(false);
    }
  }

  async function handleRefreshPersonalDrivers() {
    setPersonalDriverLoading(true);
    try {
      await recomputePersonalDrivers(USER_ID, 28);
      const personal = await fetchPersonalDrivers(USER_ID, 50);
      setPersonalDrivers(personal.items || []);
    } catch (error) {
      console.error("Failed to refresh personal drivers", error);
      alert("Failed to refresh personal drivers. Please try again.");
    } finally {
      setPersonalDriverLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  if (loading && !dailyNarrative && insights.length === 0) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile-first single column layout */}
      <div className="max-w-md mx-auto p-4 space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-900">Daily Home</h1>
          <button
            onClick={() => navigate("/settings")}
            className="text-sm text-gray-600"
          >
            Settings
          </button>
        </div>

        {/* Disclaimer (always visible) */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-gray-700">
          <div className="font-semibold mb-1">Not medical advice</div>
          <div>This app analyzes patterns. It does not diagnose conditions or replace clinicians.</div>
        </div>

        {/* TOP SECTION — Today's Summary */}
        <div className="bg-white rounded-lg p-4 space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Today's Summary</h2>
          {dailyNarrative ? (
            <NarrativeCard narrative={dailyNarrative} />
          ) : (
            <div className="text-sm text-gray-500">
              No summary yet. Complete your daily check-in to generate insights.
            </div>
          )}
        </div>

        {/* MIDDLE SECTION — Inbox */}
        <div className="bg-white rounded-lg p-4 space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Inbox</h2>
          {inboxItems.length > 0 ? (
            <InboxPanel userId={USER_ID} />
          ) : (
            <div className="text-sm text-gray-500">No new items</div>
          )}
        </div>

        {/* Driver Associations */}
        <div className="bg-white rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Driver Associations</h2>
            <button
              onClick={handleRefreshDrivers}
              disabled={driverLoading}
              className="text-xs bg-blue-600 text-white px-3 py-1 rounded disabled:bg-gray-400"
            >
              {driverLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          <DriversPanel findings={driverFindings} loading={driverLoading} />
        </div>

        {/* Personal Drivers */}
        <div className="bg-white rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Personal Drivers</h2>
            <button
              onClick={handleRefreshPersonalDrivers}
              disabled={personalDriverLoading}
              className="text-xs bg-blue-600 text-white px-3 py-1 rounded disabled:bg-gray-400"
            >
              {personalDriverLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          <PersonalDriversPanel drivers={personalDrivers} loading={personalDriverLoading} />
        </div>

        {/* BOTTOM SECTION — Actions */}
        <div className="space-y-2">
          <button
            onClick={() => setShowCheckIn(true)}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium"
          >
            Log today
          </button>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => navigate("/metrics")}
              className="bg-white border border-gray-300 text-gray-700 py-2 rounded-lg text-sm"
            >
              View metrics
            </button>
            <button
              onClick={() => navigate("/insights")}
              className="bg-white border border-gray-300 text-gray-700 py-2 rounded-lg text-sm"
            >
              View insights
            </button>
          </div>
        </div>

        {/* Check-in modal */}
        {showCheckIn && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
              <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-semibold">Daily Check-in</h2>
                <button
                  onClick={() => setShowCheckIn(false)}
                  className="text-gray-500"
                >
                  ✕
                </button>
              </div>
              <div className="p-4">
                <DailyCheckIn
                  onComplete={() => {
                    setShowCheckIn(false);
                    loadAll();
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
