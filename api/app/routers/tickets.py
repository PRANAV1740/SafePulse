"""Intervention tickets for human review."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Cluster, ClusterReport, Ticket
from app.schemas import TicketOut, TicketStatusUpdate
from app.services.scoring import DISCLAIMER


def _ticket_out(t: Ticket) -> TicketOut:
    return TicketOut(
        id=t.id,
        cluster_id=t.cluster_id,
        title=t.title,
        summary=t.summary,
        review_urgency=t.review_urgency,
        evidence_confidence=t.evidence_confidence,
        location_confidence=t.location_confidence,
        composite_priority=t.composite_priority,
        disclaimer=t.disclaimer,
        status=t.status,
        evidence=t.evidence,
        created_at=t.created_at,
    )


def generate_tickets(session: Session) -> list[Ticket]:
    """Create one ticket per cluster that does not yet have one; refresh scores."""
    tickets: list[Ticket] = []
    clusters = session.exec(select(Cluster)).all()
    for cluster in clusters:
        report_ids = [
            cr.report_id
            for cr in session.exec(
                select(ClusterReport).where(ClusterReport.cluster_id == cluster.id)
            ).all()
        ]
        ticket = session.exec(select(Ticket).where(Ticket.cluster_id == cluster.id)).first()
        if ticket is None:
            ticket = Ticket(
                cluster_id=cluster.id,
                title=f"{cluster.hazard_type.value.replace('_', ' ').title()} "
                f"near {cluster.center_lat:.4f}, {cluster.center_lon:.4f}",
                disclaimer=DISCLAIMER,
            )
        ticket.summary = (
            f"{cluster.report_count} report(s). "
            f"Review urgency {cluster.review_urgency}, evidence confidence "
            f"{cluster.evidence_confidence}, location confidence "
            f"{cluster.location_confidence}."
        )
        ticket.review_urgency = cluster.review_urgency
        ticket.evidence_confidence = cluster.evidence_confidence
        ticket.location_confidence = cluster.location_confidence
        ticket.composite_priority = cluster.composite_priority
        ticket.evidence = report_ids
        session.add(ticket)
        tickets.append(ticket)
    session.commit()
    for t in tickets:
        session.refresh(t)
    return tickets


router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketOut])
def list_tickets(session: Session = Depends(get_session)) -> list[TicketOut]:
    generate_tickets(session)
    tickets = session.exec(select(Ticket).order_by(Ticket.composite_priority.desc())).all()
    return [_ticket_out(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, session: Session = Depends(get_session)) -> TicketOut:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_out(ticket)


@router.post("/{ticket_id}/status", response_model=TicketOut)
def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    session: Session = Depends(get_session),
) -> TicketOut:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = payload.status
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return _ticket_out(ticket)
