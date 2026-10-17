"""SQLModel database tables.

Design guardrails:
- Extraction never carries coordinates; location only ever comes from the
  deterministic resolver (bundled segments, gazetteer, Nominatim, or a
  user-asserted manual pin).
- Review urgency, evidence confidence and location confidence are stored as
  three separate fields and are never collapsed before storage.
- Uncertain duplicates are marked `possible_duplicate` and are neither merged,
  discarded, nor counted as corroboration until a human resolves them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Language(str, Enum):
    en = "en"
    hi = "hi"
    pa = "pa"


class HazardType(str, Enum):
    pothole = "pothole"
    waterlogging = "waterlogging"
    fallen_tree = "fallen_tree"
    broken_signal = "broken_signal"
    debris = "debris"
    accident = "accident"
    other = "other"


class ReportStatus(str, Enum):
    pending = "pending"
    needs_clarification = "needs_clarification"
    resolved = "resolved"


class ReviewQueue(str, Enum):
    normal = "normal"
    # Urgent but not yet verified: routed here instead of being suppressed by a
    # low composite confidence score.
    urgent_verification = "urgent_verification"


class DuplicateStatus(str, Enum):
    none = "none"
    possible_duplicate = "possible_duplicate"
    confirmed_duplicate = "confirmed_duplicate"


class ResolutionMethod(str, Enum):
    bundled_segment = "bundled_segment"
    gazetteer = "gazetteer"
    nominatim = "nominatim"
    manual_pin = "manual_pin"
    unresolved = "unresolved"


class ProvenanceType(str, Enum):
    real_reference = "real_reference"
    consent_based = "consent_based"
    synthetic = "synthetic"


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: int | None = Field(default=None, primary_key=True)
    raw_text: str
    language: Language = Field(default=Language.en)
    status: ReportStatus = Field(default=ReportStatus.pending)
    review_queue: ReviewQueue = Field(default=ReviewQueue.normal)
    duplicate_status: DuplicateStatus = Field(default=DuplicateStatus.none)
    possible_duplicate_of: int | None = Field(default=None, foreign_key="reports.id")

    is_synthetic: bool = Field(default=False)
    provenance_source_type: ProvenanceType = Field(default=ProvenanceType.consent_based)
    provenance_source: str = Field(default="user_submission")
    provenance_note: str = Field(default="")

    created_at: datetime = Field(default_factory=_utcnow)


class Extraction(SQLModel, table=True):
    __tablename__ = "extractions"

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id")
    hazard_type: HazardType = Field(default=HazardType.other)
    severity_hint: str = Field(default="unknown")
    landmarks: list = Field(default_factory=list, sa_column=Column(JSON))
    direction_clues: list = Field(default_factory=list, sa_column=Column(JSON))
    confidence: float = Field(default=0.0)
    raw_model_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    model_version: str = Field(default="")
    extractor_mode: str = Field(default="stub")  # "live" | "stub"


class Location(SQLModel, table=True):
    __tablename__ = "locations"

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id")
    resolved_lat: float | None = Field(default=None)
    resolved_lon: float | None = Field(default=None)
    resolved_name: str = Field(default="")
    confidence: float = Field(default=0.0)
    method: ResolutionMethod = Field(default=ResolutionMethod.unresolved)
    segment_ref: str = Field(default="")
    candidate_count: int = Field(default=0)


class Candidate(SQLModel, table=True):
    __tablename__ = "candidates"

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reports.id")
    name: str
    lat: float
    lon: float
    segment_id: str = Field(default="")
    osm_ref: str = Field(default="")
    geometry_source: str = Field(default="")  # "bundled_segment" | "nominatim" | ...
    rank_score: float = Field(default=0.0)
    rank_reason: str = Field(default="")


class Cluster(SQLModel, table=True):
    __tablename__ = "clusters"

    id: int | None = Field(default=None, primary_key=True)
    hazard_type: HazardType = Field(default=HazardType.other)
    center_lat: float | None = Field(default=None)
    center_lon: float | None = Field(default=None)
    report_count: int = Field(default=0)
    review_urgency: float = Field(default=0.0)
    evidence_confidence: float = Field(default=0.0)
    location_confidence: float = Field(default=0.0)
    composite_priority: float = Field(default=0.0)
    score_breakdown: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_utcnow)


class ClusterReport(SQLModel, table=True):
    __tablename__ = "cluster_reports"

    id: int | None = Field(default=None, primary_key=True)
    cluster_id: int = Field(foreign_key="clusters.id")
    report_id: int = Field(foreign_key="reports.id")


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: int | None = Field(default=None, primary_key=True)
    cluster_id: int = Field(foreign_key="clusters.id")
    title: str
    summary: str = Field(default="")
    review_urgency: float = Field(default=0.0)
    evidence_confidence: float = Field(default=0.0)
    location_confidence: float = Field(default=0.0)
    composite_priority: float = Field(default=0.0)
    disclaimer: str = Field(
        default=(
            "Priority is a triage heuristic for ordering human review. "
            "It is not an accident probability or a safety guarantee."
        )
    )
    status: str = Field(default="open")  # open | reviewing | closed
    evidence: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utcnow)


class GeocodeCache(SQLModel, table=True):
    __tablename__ = "geocode_cache"

    id: int | None = Field(default=None, primary_key=True)
    query: str = Field(index=True, unique=True)
    lat: float | None = Field(default=None)
    lon: float | None = Field(default=None)
    display_name: str = Field(default="")
    raw: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utcnow)
