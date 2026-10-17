"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Candidate, ReportSubmitResponse } from "@/lib/types";

export function ClarificationPrompt({
  reportId,
  candidates,
  onResolved,
}: {
  reportId: number;
  candidates: Candidate[];
  onResolved: (res: ReportSubmitResponse) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function choose(body: { candidate_id?: number; manual_pin?: { lat: number; lon: number } }) {
    setBusy(true);
    setError(null);
    try {
      onResolved(await api.clarify(reportId, body));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded border border-slate-300 bg-white p-4">
      <p className="mb-2 font-medium">
        The location is ambiguous. Pick the closest match (we never guess
        coordinates):
      </p>
      <ul className="space-y-2">
        {candidates.map((c) => (
          <li key={c.id}>
            <button
              type="button"
              disabled={busy}
              onClick={() => choose({ candidate_id: c.id })}
              className="w-full rounded border px-3 py-2 text-left hover:bg-slate-50 disabled:opacity-50"
            >
              <span className="font-medium">{c.name}</span>
              <span className="block text-xs text-slate-500">
                {c.geometry_source} · {c.rank_reason}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        disabled={busy}
        onClick={() => choose({ manual_pin: { lat: 30.7333, lon: 76.7794 } })}
        className="mt-3 text-sm text-sky-700 underline disabled:opacity-50"
      >
        None of these — drop a pin at city centre (demo)
      </button>
      {error && <p className="mt-2 text-sm text-rose-700">{error}</p>}
    </div>
  );
}
