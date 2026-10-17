import Link from "next/link";
import type { Ticket } from "@/lib/types";
import { PriorityBadge } from "./PriorityBadge";

export function TicketCard({ ticket }: { ticket: Ticket }) {
  return (
    <div className="rounded border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <Link href={`/tickets/${ticket.id}`} className="font-medium text-slate-900 hover:underline">
          {ticket.title}
        </Link>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{ticket.status}</span>
      </div>
      <p className="mt-1 text-sm text-slate-600">{ticket.summary}</p>
      <div className="mt-3">
        <PriorityBadge
          urgency={ticket.review_urgency}
          evidence={ticket.evidence_confidence}
          location={ticket.location_confidence}
        />
      </div>
      <p className="mt-2 text-xs text-slate-400">{ticket.disclaimer}</p>
    </div>
  );
}
