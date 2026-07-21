"""
Event Sourcing Models — Append-only event store for full auditability.
Replays events to rebuild aggregate state for any entity at any point in time.
"""
from sqlalchemy import (
    String, Text, ForeignKey, DateTime, Integer, Column, Index, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
from ..db.database import Base
from .models import TimestampMixin, SafeJSONB


class DomainEvent(Base, TimestampMixin):
    """
    Append-only event log. Every state-changing operation produces an event.
    Events are immutable — never updated or deleted.
    Used for: audit trail, CQRS projections, temporal queries, replay.
    """
    __tablename__ = "domain_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Aggregate identifiers
    aggregate_type: Mapped[str] = mapped_column(String(50), index=True)
        # e.g., "candidate", "application", "job_posting", "offer"
    aggregate_id: Mapped[int] = mapped_column(index=True)

    # Event metadata
    event_type: Mapped[str] = mapped_column(String(100), index=True)
        # e.g., "candidate.created", "application.scored", "offer.sent"
    event_version: Mapped[int] = mapped_column(default=1)
        # Monotonically increasing per aggregate — enables optimistic concurrency

    # Who
    actor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )

    # What
    payload_before: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
        # Snapshot of aggregate BEFORE the event (for diff/rollback)
    payload_after: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
        # Snapshot of aggregate AFTER the event
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        # Human-readable summary of changed fields

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
        # Links events across services (tracing)
    causation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
        # Parent event that caused this event

    source_service: Mapped[str] = mapped_column(String(50), default="api")
        # Which microservice emitted this event

    __table_args__ = (
        Index("ix_domain_events_aggregate", "aggregate_type", "aggregate_id", "event_version"),
        Index("ix_domain_events_org_type_time", "org_id", "aggregate_type", "created_at"),
        Index("ix_domain_events_correlation", "correlation_id"),
        Index("ix_domain_events_created_brin", "created_at", postgresql_using="brin"),
    )


class EventProjection(Base, TimestampMixin):
    """
    CQRS Read Model — pre-computed projections updated by events.
    Reduces query load by maintaining denormalized views.
    """
    __tablename__ = "event_projections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    projection_name: Mapped[str] = mapped_column(String(100), index=True)
        # e.g., "candidate_scoreboard", "hiring_funnel", "recruiter_performance"
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    snapshot_data: Mapped[dict] = mapped_column(SafeJSONB, default=dict)
    last_event_id: Mapped[int] = mapped_column(index=True)
        # ID of the last processed DomainEvent (for idempotent replay)

    __table_args__ = (
        Index("ix_event_projections_name_org", "projection_name", "org_id", unique=True),
    )
