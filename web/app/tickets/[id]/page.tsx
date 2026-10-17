"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import { PriorityBadge } from "@/components/PriorityBadge";
import type { Ticket } from "@/lib/types";

const STATUSES = ["open", "reviewing", "closed"];

export default function TicketDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const res = await fetch(`${API_BASE}/api/tickets/${id}`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      setTicket((await res.json()) as Ticket);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function setStatus(status: string) {
    const res = await fetch(`${API_BASE}/api/tickets/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (res.ok) setTicket((await res.json()) as Ticket);
  }

  if (error) return <p className="text-sm text-rose-700">{error}</p>;
  if (!ticket) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{ticket.title}</h1>
      <p className="text-sm text-slate-600">{ticket.summary}</p>
      <PriorityBadge
        urgency={ticket.review_urgency}
        evidence={ticket.evidence_confidence}
        location={ticket.location_confidence}
      />
      <div className="rounded border bg-white p-3 text-sm">
        <p>
          <strong>Evidence reports:</strong>{" "}
          {ticket.evidence.join(", ") || "—"}
        </p>
        <p className="mt-2 text-xs text-slate-400">{ticket.disclaimer}</p>
      </div>
      <div className="flex gap-2">
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatus(s)}
            className={`rounded border px-3 py-1 text-sm ${
              ticket.status === s ? "bg-slate-900 text-white" : "bg-white"
            }`}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
