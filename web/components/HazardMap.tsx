"use client";

import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";
import type { Cluster } from "@/lib/types";

const CHANDIGARH: [number, number] = [30.7333, 76.7794];

export function HazardMap({ clusters }: { clusters: Cluster[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (cancelled || !ref.current || mapRef.current) return;

      const map = L.map(ref.current).setView(CHANDIGARH, 13);
      mapRef.current = map;
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors",
      }).addTo(map);

      for (const c of clusters) {
        if (c.center_lat == null || c.center_lon == null) continue;
        const radius = 6 + c.report_count * 2;
        L.circleMarker([c.center_lat, c.center_lon], {
          radius,
          color: "#be123c",
          fillColor: "#fb7185",
          fillOpacity: 0.6,
        })
          .addTo(map)
          .bindPopup(
            `<strong>${c.hazard_type}</strong><br/>reports: ${c.report_count}<br/>` +
              `urgency ${Math.round(c.review_urgency * 100)}% · ` +
              `evidence ${Math.round(c.evidence_confidence * 100)}% · ` +
              `location ${Math.round(c.location_confidence * 100)}%`,
          );
      }
    })();

    return () => {
      cancelled = true;
      const m = mapRef.current as { remove?: () => void } | null;
      m?.remove?.();
      mapRef.current = null;
    };
  }, [clusters]);

  return <div ref={ref} className="h-[520px] w-full rounded border" />;
}
