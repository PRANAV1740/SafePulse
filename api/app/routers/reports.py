"""Report ingestion, listing, detail, and clarification."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    Candidate,
    DuplicateStatus,
    Extraction,
    Location,
    ProvenanceType,
    Report,
    ReportStatus,
    ResolutionMethod,
    ReviewQueue,
)
from app.schemas import (
    CandidateOut,
    ClarifyRequest,
    ExtractionOut,
    LocationOut,
    ProvenanceOut,
    ReportCreate,
    ReportOut,
    ReportSubmitResponse,
)
from app.services import clustering, scoring
from app.services.gemini import get_extractor
from app.services.geocoder import ResolutionResult, resolve_location

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _report_out(session: Session, report: Report) -> ReportOut:
    ext = session.exec(select(Extraction).where(Extraction.report_id == report.id)).first()
    loc = session.exec(select(Location).where(Location.report_id == report.id)).first()
    cands = session.exec(select(Candidate).where(Candidate.report_id == report.id)).all()
    return ReportOut(
        id=report.id,
        raw_text=report.raw_text,
        language=report.language,
        status=report.status,
        review_queue=report.review_queue,
        duplicate_status=report.duplicate_status,
        possible_duplicate_of=report.possible_duplicate_of,
        is_synthetic=report.is_synthetic,
        provenance=ProvenanceOut(
            source_type=report.provenance_source_type,
            source=report.provenance_source,
            note=report.provenance_note,
        ),
        created_at=report.created_at,
        extraction=(
            ExtractionOut(
                hazard_type=ext.hazard_type,
                severity_hint=ext.severity_hint,
                landmarks=ext.landmarks,
                direction_clues=ext.direction_clues,
                confidence=ext.confidence,
                extractor_mode=ext.extractor_mode,
            )
            if ext
            else None
        ),
        location=(
            LocationOut(
                resolved_lat=loc.resolved_lat,
                resolved_lon=loc.resolved_lon,
                resolved_name=loc.resolved_name,
                confidence=loc.confidence,
                method=loc.method,
                candidate_count=loc.candidate_count,
            )
            if loc
            else None
        ),
        candidates=[
            CandidateOut(
                id=c.id,
                name=c.name,
                lat=c.lat,
                lon=c.lon,
                geometry_source=c.geometry_source,
                rank_score=c.rank_score,
                rank_reason=c.rank_reason,
            )
            for c in cands
        ],
    )


def _persist_resolution(session: Session, report: Report, result: ResolutionResult) -> None:
    """Store/replace location + candidate rows and set the report status + queue."""
    for row in session.exec(select(Candidate).where(Candidate.report_id == report.id)).all():
        session.delete(row)
    loc = session.exec(select(Location).where(Location.report_id == report.id)).first()
    if loc is None:
        loc = Location(report_id=report.id)

    loc.resolved_lat = result.resolved_lat
    loc.resolved_lon = result.resolved_lon
    loc.resolved_name = result.resolved_name
    loc.confidence = result.confidence
    loc.method = result.method
    loc.segment_ref = result.segment_ref
    loc.candidate_count = result.candidate_count
    session.add(loc)

    for cand in result.candidates:
        session.add(
            Candidate(
                report_id=report.id,
                name=cand["name"],
                lat=cand["lat"],
                lon=cand["lon"],
                segment_id=cand.get("segment_id", ""),
                osm_ref=cand.get("osm_ref", ""),
                geometry_source=cand.get("geometry_source", ""),
                rank_score=cand.get("rank_score", 0.0),
                rank_reason=cand.get("rank_reason", ""),
            )
        )

    report.status = (
        ReportStatus.needs_clarification
        if result.needs_clarification
        else ReportStatus.resolved
    )
    session.add(report)
    session.commit()


def _apply_routing(session: Session, report: Report, hazard, severity: str, result) -> None:
    """Route urgent-but-unverified reports to the urgent-verification queue."""
    urgency = scoring.review_urgency(hazard, severity)
    resolved = not result.needs_clarification and result.resolved_lat is not None
    evidence = scoring.evidence_confidence(1, _extraction_conf(session, report.id))
    location = scoring.location_confidence([result.confidence] if resolved else [])
    if scoring.is_urgent_unverified(urgency, evidence, location):
        report.review_queue = ReviewQueue.urgent_verification
    else:
        report.review_queue = ReviewQueue.normal
    session.add(report)
    session.commit()


def _extraction_conf(session: Session, report_id: int) -> float:
    ext = session.exec(select(Extraction).where(Extraction.report_id == report_id)).first()
    return ext.confidence if ext else 0.0


@router.post("", response_model=ReportSubmitResponse)
def submit_report(
    payload: ReportCreate,
    session: Session = Depends(get_session),
) -> ReportSubmitResponse:
    report = Report(
        raw_text=payload.text,
        language=payload.language,
        provenance_source_type=ProvenanceType.consent_based,
        provenance_source="user_submission",
        provenance_note="Submitted via public report form.",
    )
    session.add(report)
    session.commit()
    session.refresh(report)

    extractor = get_extractor()
    extracted = extractor.extract(payload.text, payload.language.value)
    ext = Extraction(
        report_id=report.id,
        hazard_type=extracted["hazard_type"],
        severity_hint=extracted["severity_hint"],
        landmarks=extracted["landmarks"],
        direction_clues=extracted["direction_clues"],
        confidence=extracted["confidence"],
        raw_model_json=extracted.get("raw", {}),
        model_version=extracted.get("model_version", ""),
        extractor_mode=extracted["extractor_mode"],
    )
    session.add(ext)
    session.commit()

    manual_pin = payload.manual_pin.model_dump() if payload.manual_pin else None
    result = resolve_location(extracted, manual_pin, session)
    _persist_resolution(session, report, result)

    # Duplicate detection: mark uncertain matches, never merge/discard.
    dup = clustering.detect_possible_duplicate(session, report)
    if dup is not None:
        report.duplicate_status = DuplicateStatus.possible_duplicate
        report.possible_duplicate_of = dup.id
        session.add(report)
        session.commit()

    _apply_routing(session, report, extracted["hazard_type"], extracted["severity_hint"], result)

    if report.status == ReportStatus.resolved:
        clustering.rebuild_clusters(session)

    session.refresh(report)
    message = (
        "Location ambiguous — please choose a candidate or drop a map pin."
        if result.needs_clarification
        else "Report resolved and queued for review."
    )
    return ReportSubmitResponse(
        report=_report_out(session, report),
        needs_clarification=result.needs_clarification,
        message=message,
    )


@router.post("/{report_id}/clarify", response_model=ReportSubmitResponse)
def clarify_report(
    report_id: int,
    payload: ClarifyRequest,
    session: Session = Depends(get_session),
) -> ReportSubmitResponse:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if payload.manual_pin is not None:
        loc = session.exec(select(Location).where(Location.report_id == report_id)).first() or (
            Location(report_id=report_id)
        )
        loc.resolved_lat = payload.manual_pin.lat
        loc.resolved_lon = payload.manual_pin.lon
        loc.resolved_name = "User-selected map pin"
        loc.confidence = 0.6
        loc.method = ResolutionMethod.manual_pin
        session.add(loc)
    elif payload.candidate_id is not None:
        cand = session.get(Candidate, payload.candidate_id)
        if cand is None or cand.report_id != report_id:
            raise HTTPException(status_code=400, detail="Invalid candidate for this report")
        loc = session.exec(select(Location).where(Location.report_id == report_id)).first() or (
            Location(report_id=report_id)
        )
        loc.resolved_lat = cand.lat
        loc.resolved_lon = cand.lon
        loc.resolved_name = cand.name
        loc.confidence = max(cand.rank_score, 0.5)
        loc.method = (
            ResolutionMethod.bundled_segment
            if cand.geometry_source == "bundled_segment"
            else ResolutionMethod.gazetteer
        )
        session.add(loc)
    else:
        raise HTTPException(status_code=400, detail="Provide candidate_id or manual_pin")

    report.status = ReportStatus.resolved
    session.add(report)
    session.commit()
    clustering.rebuild_clusters(session)
    session.refresh(report)
    return ReportSubmitResponse(
        report=_report_out(session, report),
        needs_clarification=False,
        message="Clarification accepted; report resolved.",
    )


@router.get("", response_model=list[ReportOut])
def list_reports(
    session: Session = Depends(get_session),
    status: ReportStatus | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> list[ReportOut]:
    stmt = select(Report).order_by(Report.created_at.desc())
    if status is not None:
        stmt = stmt.where(Report.status == status)
    reports = session.exec(stmt.offset(offset).limit(limit)).all()
    return [_report_out(session, r) for r in reports]


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, session: Session = Depends(get_session)) -> ReportOut:
    report = session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_out(session, report)
