import React, { useState } from "react";
import { createIntervention } from "../api/interventions";
import { SafetyBadge, SafetyDetails } from "./SafetyBadge";

const USER_ID = 1;

export function InterventionCreate() {
  const [key, setKey] = useState("magnesium_glycinate");
  const [name, setName] = useState("Magnesium glycinate");
  const [dosage, setDosage] = useState("200mg");
  const [schedule, setSchedule] = useState("Evening");

  // MVP safety flags (expand later via onboarding)
  const [pregnant, setPregnant] = useState(false);
  const [kidneyDisease, setKidneyDisease] = useState(false);

  const [created, setCreated] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setLoading(true);
    setError(null);
    setCreated(null);
    try {
      const res = await createIntervention({
        user_id: USER_ID,
        key,
        name,
        dosage,
        schedule,
        user_flags: {
          pregnant,
          kidney_disease: kidneyDisease,
        },
      } as any);
      setCreated(res);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to create intervention");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl shadow p-4 bg-white">
      <div className="text-lg font-semibold mb-2">Add Intervention (MVP)</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="text-sm text-gray-600">Intervention key</label>
          <select
            className="w-full border rounded-lg p-2"
            value={key}
            onChange={(e) => {
              const k = e.target.value;
              setKey(k);
              setName(
                k === "melatonin"
                  ? "Melatonin"
                  : k === "omega_3"
                  ? "Omega 3"
                  : "Magnesium glycinate"
              );
            }}
          >
            <option value="magnesium_glycinate">magnesium_glycinate</option>
            <option value="melatonin">melatonin</option>
            <option value="omega_3">omega_3</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-gray-600">Name</label>
          <input className="w-full border rounded-lg p-2" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-sm text-gray-600">Dosage</label>
          <input className="w-full border rounded-lg p-2" value={dosage} onChange={(e) => setDosage(e.target.value)} />
        </div>
        <div>
          <label className="text-sm text-gray-600">Schedule</label>
          <input className="w-full border rounded-lg p-2" value={schedule} onChange={(e) => setSchedule(e.target.value)} />
        </div>
      </div>

      <div className="mt-3">
        <div className="text-sm text-gray-600 mb-2">Safety flags (MVP)</div>
        <div className="flex gap-3 items-center">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={pregnant} onChange={(e) => setPregnant(e.target.checked)} />
            <span>Pregnant</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={kidneyDisease} onChange={(e) => setKidneyDisease(e.target.checked)} />
            <span>Kidney disease</span>
          </label>
        </div>
      </div>

      <button
        onClick={onSubmit}
        disabled={loading}
        className="mt-4 px-4 py-2 rounded-xl bg-black text-white disabled:opacity-50"
      >
        {loading ? "Creating..." : "Create intervention"}
      </button>

      {error && <div className="mt-3 text-red-600 text-sm">{error}</div>}

      {created && (
        <div className="mt-4 border rounded-xl p-3">
          <div className="font-medium">Created</div>
          <div className="text-sm text-gray-700">{created.name} ({created.key})</div>
          {created.safety_risk_level && (
            <div className="mt-2">
              <SafetyBadge
                safety={{
                  risk: created.safety_risk_level,
                  evidence_grade: created.safety_evidence_grade,
                  boundary: created.safety_boundary,
                  issues: created.safety_issues ?? [],
                }}
              />
              <SafetyDetails
                safety={{
                  risk: created.safety_risk_level,
                  evidence_grade: created.safety_evidence_grade,
                  boundary: created.safety_boundary,
                  issues: created.safety_issues ?? [],
                }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

