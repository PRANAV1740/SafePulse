"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Cluster } from "@/lib/types";

const HazardMap = dynamic(
  () => import("@/components/HazardMap").then((m) => m.HazardMap),
  { ssr: false, loading: () => <p className="text-sm text-slate-500">Loading map…</p> },
);

export default function MapPage() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listClusters().then(setClusters).catch((e) => setError((e as Error).message));
  }, []);

  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">Hazard map</h1>
      {error && <p className="text-sm text-rose-700">{error}</p>}
      <HazardMap clusters={clusters} />
      <p className="text-xs text-slate-500">
        {clusters.length} cluster(s). Marker size reflects report count, not
        certainty.
      </p>
    </div>
  );
}
