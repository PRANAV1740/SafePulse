// Mirrors the FastAPI DTOs in api/app/schemas.py.

export type Language = "en" | "hi" | "pa";

export type HazardType =
  | "pothole"
  | "waterlogging"
  | "fallen_tree"
  | "broken_signal"
  | "debris"
  | "accident"
  | "other";

export type ReportStatus = "pending" | "needs_clarification" | "resolved";
export type ReviewQueue = "normal" | "urgent_verification";
export type DuplicateStatus = "none" | "possible_duplicate" | "confirmed_duplicate";
export type ResolutionMethod =
  | "bundled_segment"
  | "gazetteer"
  | "nominatim"
  | "manual_pin"
  | "unresolved";
export type ProvenanceType = "real_reference" | "consent_based" | "synthetic";

export interface ManualPin {
  lat: number;
  lon: number;
}

export interface Extraction {
  hazard_type: HazardType;
  severity_hint: string;
  landmarks: string[];
  direction_clues: string[];
  confidence: number;
  extractor_mode: "live" | "stub";
}

export interface Candidate {
  id: number;
  name: string;
  lat: number;
  lon: number;
  geometry_source: string;
  rank_score: number;
  rank_reason: string;
}

export interface LocationOut {
  resolved_lat: number | null;
  resolved_lon: number | null;
  resolved_name: string;
  confidence: number;
  method: ResolutionMethod;
  candidate_count: number;
}

export interface Provenance {
  source_type: ProvenanceType;
  source: string;
  note: string;
}

export interface Report {
  id: number;
  raw_text: string;
  language: Language;
  status: ReportStatus;
  review_queue: ReviewQueue;
  duplicate_status: DuplicateStatus;
  possible_duplicate_of: number | null;
  is_synthetic: boolean;
  provenance: Provenance;
  created_at: string;
  extraction: Extraction | null;
  location: LocationOut | null;
  candidates: Candidate[];
}

export interface ReportSubmitResponse {
  report: Report;
  needs_clarification: boolean;
  message: string;
}

export interface Cluster {
  id: number;
  hazard_type: HazardType;
  center_lat: number | null;
  center_lon: number | null;
  report_count: number;
  review_urgency: number;
  evidence_confidence: number;
  location_confidence: number;
  composite_priority: number;
  score_breakdown: Record<string, unknown>;
}

export interface Ticket {
  id: number;
  cluster_id: number;
  title: string;
  summary: string;
  review_urgency: number;
  evidence_confidence: number;
  location_confidence: number;
  composite_priority: number;
  disclaimer: string;
  status: string;
  evidence: number[];
  created_at: string;
}

export interface Health {
  status: string;
  gemini_configured: boolean;
  extractor_mode: "live" | "stub";
  nominatim_enabled: boolean;
}
