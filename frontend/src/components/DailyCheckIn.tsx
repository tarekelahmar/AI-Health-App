import React, { useState, useEffect } from "react";
import { getCheckIn, upsertCheckIn } from "../api/checkins";

const USER_ID = 1; // TODO: Get from auth context

interface CheckInData {
  sleep_quality: number;
  energy: number;
  mood: number;
  stress: number;
  notes: string;
  behaviors: {
    magnesium: boolean;
    melatonin: boolean;
    omega3: boolean;
    alcohol: boolean;
    caffeine_pm: boolean;
    exercise: boolean;
  };
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function DailyCheckIn({ onComplete }: { onComplete?: () => void }) {
  const [data, setData] = useState<CheckInData>({
    sleep_quality: 5,
    energy: 5,
    mood: 5,
    stress: 5,
    notes: "",
    behaviors: {
      magnesium: false,
      melatonin: false,
      omega3: false,
      alcohol: false,
      caffeine_pm: false,
      exercise: false,
    },
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const checkin = await getCheckIn(USER_ID, todayISO());
        if (checkin) {
          setData({
            sleep_quality: checkin.sleep_quality || 5,
            energy: checkin.energy || 5,
            mood: checkin.mood || 5,
            stress: checkin.stress || 5,
            notes: checkin.notes || "",
            behaviors: checkin.behaviors_json || {
              magnesium: false,
              melatonin: false,
              omega3: false,
              alcohol: false,
              caffeine_pm: false,
              exercise: false,
            },
          });
        }
      } catch (error) {
        console.error("Failed to load check-in", error);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await upsertCheckIn({
        user_id: USER_ID,
        checkin_date: todayISO(),
        sleep_quality: data.sleep_quality,
        energy: data.energy,
        mood: data.mood,
        stress: data.stress,
        notes: data.notes,
        behaviors_json: data.behaviors,
      });
      if (onComplete) {
        onComplete();
      }
    } catch (error) {
      console.error("Failed to save check-in", error);
      alert("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="bg-white rounded-lg p-4 space-y-6">
      <h2 className="text-lg font-semibold text-gray-900">Daily Check-in</h2>

      {/* Sliders */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Sleep quality: {data.sleep_quality}/10
          </label>
          <input
            type="range"
            min="0"
            max="10"
            value={data.sleep_quality}
            onChange={(e) => setData({ ...data, sleep_quality: parseInt(e.target.value) })}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Energy: {data.energy}/10
          </label>
          <input
            type="range"
            min="0"
            max="10"
            value={data.energy}
            onChange={(e) => setData({ ...data, energy: parseInt(e.target.value) })}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Mood: {data.mood}/10
          </label>
          <input
            type="range"
            min="0"
            max="10"
            value={data.mood}
            onChange={(e) => setData({ ...data, mood: parseInt(e.target.value) })}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Stress: {data.stress}/10
          </label>
          <input
            type="range"
            min="0"
            max="10"
            value={data.stress}
            onChange={(e) => setData({ ...data, stress: parseInt(e.target.value) })}
            className="w-full"
          />
        </div>
      </div>

      {/* Quick toggles */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Behaviors</label>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(data.behaviors).map(([key, value]) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={value}
                onChange={(e) =>
                  setData({
                    ...data,
                    behaviors: { ...data.behaviors, [key]: e.target.checked },
                  })
                }
              />
              <span className="text-sm text-gray-700 capitalize">{key.replace("_", " ")}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Notes (optional)</label>
        <textarea
          value={data.notes}
          onChange={(e) => setData({ ...data, notes: e.target.value })}
          className="w-full border border-gray-300 rounded-lg p-2 text-sm"
          rows={3}
          placeholder="Any additional notes..."
        />
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium disabled:bg-gray-400"
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </div>
  );
}

