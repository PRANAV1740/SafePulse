"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TicketCard } from "@/components/TicketCard";
import type { Ticket } from "@/lib/types";

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listTickets().then(setTickets).catch((e) => setError((e as Error).message));
  }, []);

  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold">Intervention tickets</h1>
      <p className="text-sm text-slate-600">
        Ordered by a triage heuristic for human review — not an accident
        probability.
      </p>
      {error && <p className="text-sm text-rose-700">{error}</p>}
      {tickets.length === 0 && !error && (
        <p className="text-sm text-slate-500">No tickets yet.</p>
      )}
      <div className="space-y-3">
        {tickets.map((t) => (
          <TicketCard key={t.id} ticket={t} />
        ))}
      </div>
    </div>
  );
}
