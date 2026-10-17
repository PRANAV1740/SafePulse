"use client";

import type { Health } from "@/lib/types";

/** Persistent banner shown whenever extraction is simulated (stub mode).
 *  It must never let simulated extraction look like live verified data. */
export function DemoBanner({ health }: { health: Health | null }) {
  if (!health || health.extractor_mode !== "stub") return null;
  return (
    <div
      role="status"
      className="mb-4 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
    >
      <strong>Demo mode:</strong> hazard extraction is <em>simulated</em>, not
      live AI. Results shown here are not verified incident data.
    </div>
  );
}
