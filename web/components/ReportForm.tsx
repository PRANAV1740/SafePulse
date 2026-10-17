"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health, Language, ReportSubmitResponse } from "@/lib/types";
import { ClarificationPrompt } from "./ClarificationPrompt";
import { DemoBanner } from "./DemoBanner";

const LANGUAGES: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी (Hindi)" },
  { value: "pa", label: "ਪੰਜਾਬੀ (Punjabi)" },
];

export function ReportForm() {
  const [text, setText] = useState("");
  const [language, setLanguage] = useState<Language>("en");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReportSubmitResponse | null>(null);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.submitReport({ text, language }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const report = result?.report;

  return (
    <div className="space-y-4">
      <DemoBanner health={health} />

      <form onSubmit={submit} className="space-y-3 rounded border bg-white p-4">
        <label className="block text-sm font-medium" htmlFor="report-text">
          Describe the road hazard
        </label>
        <textarea
          id="report-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="e.g. Large pothole near Sector 17 Plaza"
          className="w-full rounded border px-3 py-2"
        />
        <div className="flex items-center gap-3">
          <select
            aria-label="Language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="rounded border px-2 py-2 text-sm"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={busy || !text.trim()}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Submitting…" : "Submit report"}
          </button>
        </div>
        {error && <p className="text-sm text-rose-700">{error}</p>}
      </form>

      {result && report && (
        <div className="space-y-3">
          <p className="text-sm text-slate-700">{result.message}</p>

          {result.needs_clarification ? (
            <ClarificationPrompt
              reportId={report.id}
              candidates={report.candidates}
              onResolved={setResult}
            />
          ) : (
            <div className="rounded border bg-white p-4 text-sm">
              <p>
                <strong>Hazard:</strong> {report.extraction?.hazard_type}
              </p>
              <p>
                <strong>Location:</strong>{" "}
                {report.location?.resolved_name || "—"} (
                {report.location?.method})
              </p>
              {report.review_queue === "urgent_verification" && (
                <p className="mt-2 rounded bg-rose-100 px-2 py-1 text-rose-800">
                  Routed to the urgent-verification queue (urgent but not yet
                  verified).
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
