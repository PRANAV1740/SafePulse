"""Pydantic request/response DTOs (the API contract)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models import (
    DuplicateStatus,
    HazardType,
    Language,
    ProvenanceType,
    ReportStatus,
    ResolutionMethod,
    ReviewQueue,
)


class ManualPin(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ReportCreate(BaseModel):
    """Core MVP submission: multilingual text + optional location clue + pin."""

    text: str = Field(min_length=1, max_length=2000)
    language: Language = Language.en
    location_hint: str | None = Field(default=None, max_length=300)
    manual_pin: ManualPin | None = None
    # Photo upload is intentionally deferred from the MVP (not accepted here).


class ClarifyRequest(BaseModel):
    candidate_id: int | None = None
    manual_pin: ManualPin | None = None


class ExtractionOut(BaseModel):
    hazard_type: HazardType
    severity_hint: str
    landmarks: list[str]
    direction_clues: list[str]
    confidence: float
    extractor_mode: str  # "live" | "stub"


class CandidateOut(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    geometry_source: str
    rank_score: float
    rank_reason: str


class LocationOut(BaseModel):
    resolved_lat: float | None
    resolved_lon: float | None
    resolved_name: str
    confidence: float
    method: ResolutionMethod
    candidate_count: int


class ProvenanceOut(BaseModel):
    source_type: ProvenanceType
    source: str
    note: str


class ReportOut(BaseModel):
    id: int
    raw_text: str
    language: Language
    status: ReportStatus
    review_queue: ReviewQueue
    duplicate_status: DuplicateStatus
    possible_duplicate_of: int | None
    is_synthetic: bool
    provenance: ProvenanceOut
    created_at: datetime
    extraction: ExtractionOut | None = None
    location: LocationOut | None = None
    candidates: list[CandidateOut] = []


class ReportSubmitResponse(BaseModel):
    report: ReportOut
    needs_clarification: bool
    message: str


class ClusterOut(BaseModel):
    id: int
    hazard_type: HazardType
    center_lat: float | None
    center_lon: float | None
    report_count: int
    review_urgency: float
    evidence_confidence: float
    location_confidence: float
    composite_priority: float
    score_breakdown: dict


class TicketOut(BaseModel):
    id: int
    cluster_id: int
    title: str
    summary: str
    review_urgency: float
    evidence_confidence: float
    location_confidence: float
    composite_priority: float
    disclaimer: str
    status: str
    evidence: list[int]
    created_at: datetime


class TicketStatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|reviewing|closed)$")


class HealthOut(BaseModel):
    status: str
    gemini_configured: bool
    extractor_mode: str  # "live" | "stub"
    nominatim_enabled: bool
