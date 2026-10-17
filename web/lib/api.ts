import type {
  Cluster,
  Health,
  ManualPin,
  Report,
  ReportSubmitResponse,
  Ticket,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return (await res.json()) as T;
}

export interface SubmitInput {
  text: string;
  language: string;
  location_hint?: string;
  manual_pin?: ManualPin;
}

export const api = {
  health: () => request<Health>("/api/health"),

  submitReport: (input: SubmitInput) =>
    request<ReportSubmitResponse>("/api/reports", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  clarify: (
    reportId: number,
    body: { candidate_id?: number; manual_pin?: ManualPin },
  ) =>
    request<ReportSubmitResponse>(`/api/reports/${reportId}/clarify`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listReports: () => request<Report[]>("/api/reports"),
  getReport: (id: number) => request<Report>(`/api/reports/${id}`),
  listClusters: () => request<Cluster[]>("/api/clusters"),
  listTickets: () => request<Ticket[]>("/api/tickets"),
  getTicket: (id: number) => request<Ticket>(`/api/tickets/${id}`),
};
