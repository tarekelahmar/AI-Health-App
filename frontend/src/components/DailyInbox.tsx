import { useEffect, useMemo, useState } from "react";
import type { CheckIn } from "../types/CheckIn";
import { getCheckIn, upsertCheckIn, patchCheckIn } from "../api/checkins";

const clamp = (n: number) => Math.max(0, Math.min(10, n));

type Props = {
  userId: number;
};

export default function DailyInbox({ userId }: Props) {
  const todayISO = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [checkin, setCheckin] = useState<CheckIn | null>(null);
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState("");

  async function load() {
    setLoading(true);
    try {
      const c = await getCheckIn(userId, todayISO);
      setCheckin(c);
      setNotes(c.notes ?? "");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Ensure there is a checkin row for today (upsert does that)
    (async () => {
      setLoading(true);
      try {
        const c = await upsertCheckIn({
          user_id: userId,
          checkin_date: todayISO,
          behaviors_json: {},
        });
        setCheckin(c);
        setNotes(c.notes ?? "");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function setScore(field: "sleep_quality" | "energy" | "mood" | "stress", value: number) {
    if (!checkin) return;
    const updated = await patchCheckIn(userId, todayISO, { [field]: clamp(value) } as any);
    setCheckin(updated);
  }

  async function toggleBehavior(key: string) {
    if (!checkin) return;
    const next = { ...(checkin.behaviors_json ?? {}) };
    next[key] = !next[key];
    const updated = await patchCheckIn(userId, todayISO, { behaviors_json: next } as any);
    setCheckin(updated);
  }

  async function saveNotes() {
    if (!checkin) return;
    const updated = await patchCheckIn(userId, todayISO, { notes });
    setCheckin(updated);
  }

  return (
    <div className="rounded-2xl shadow p-4 bg-white">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Today's Check-in</h2>
        <div className="text-sm text-gray-500">{todayISO}</div>
      </div>

      {loading && <div className="mt-2 text-sm text-gray-500">Loading…</div>}

      <div className="mt-4 grid grid-cols-2 gap-3">
        <ScoreRow label="Sleep quality" value={checkin?.sleep_quality} onChange={(v) => setScore("sleep_quality", v)} />
        <ScoreRow label="Energy" value={checkin?.energy} onChange={(v) => setScore("energy", v)} />
        <ScoreRow label="Mood" value={checkin?.mood} onChange={(v) => setScore("mood", v)} />
        <ScoreRow label="Stress" value={checkin?.stress} onChange={(v) => setScore("stress", v)} />
      </div>

      <div className="mt-4">
        <div className="text-sm font-medium mb-2">Quick logs</div>
        <div className="flex flex-wrap gap-2">
          <ToggleChip label="Took magnesium" active={!!checkin?.behaviors_json?.took_magnesium} onClick={() => toggleBehavior("took_magnesium")} />
          <ToggleChip label="Took melatonin" active={!!checkin?.behaviors_json?.took_melatonin} onClick={() => toggleBehavior("took_melatonin")} />
          <ToggleChip label="Omega-3" active={!!checkin?.behaviors_json?.took_omega3} onClick={() => toggleBehavior("took_omega3")} />
          <ToggleChip label="Alcohol" active={!!checkin?.behaviors_json?.had_alcohol} onClick={() => toggleBehavior("had_alcohol")} />
          <ToggleChip label="Caffeine PM" active={!!checkin?.behaviors_json?.caffeine_pm} onClick={() => toggleBehavior("caffeine_pm")} />
        </div>
      </div>

      <div className="mt-4">
        <div className="text-sm font-medium mb-2">Notes</div>
        <textarea
          className="w-full border rounded-xl p-2 text-sm"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Anything relevant today? (late meal, stress, travel, supplements…) "
        />
        <div className="mt-2 flex gap-2">
          <button className="px-3 py-2 rounded-xl bg-black text-white text-sm" onClick={saveNotes}>
            Save notes
          </button>
          <button className="px-3 py-2 rounded-xl bg-gray-100 text-sm" onClick={load}>
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}

function ScoreRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value?: number | null;
  onChange: (v: number) => void;
}) {
  const v = value ?? 0;
  return (
    <div className="border rounded-xl p-3">
      <div className="text-sm font-medium">{label}</div>
      <div className="mt-2 flex items-center gap-3">
        <input
          type="range"
          min={0}
          max={10}
          value={v}
          onChange={(e) => onChange(parseInt(e.target.value, 10))}
          className="w-full"
        />
        <div className="w-10 text-right text-sm text-gray-600">{v}</div>
      </div>
    </div>
  );
}

function ToggleChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={[
        "px-3 py-2 rounded-full text-sm border",
        active ? "bg-black text-white border-black" : "bg-white text-gray-700 border-gray-200",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

