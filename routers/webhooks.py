"""Webhook receiver endpoints."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from security import verify_signature
from config import settings

from database import get_db
from models import Event, EventStatus
from schemas import EventResponse, WebhookReceived

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/{provider}",
    response_model=WebhookReceived,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_id: str | None = Header(default=None, alias="X-Webhook-Id"),
    x_webhook_event: str | None = Header(default=None, alias="X-Webhook-Event"),
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
):
    """Receive a webhook from a provider and store it for processing.

    Returns 202 Accepted once stored. Actual processing happens asynchronously.
    """
    raw_body = await request.body()
    body_text = raw_body.decode("utf-8", errors="replace")

    # Try to parse as JSON for validation (but store the raw body regardless)
    try:
        parsed = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body is not valid JSON",
        )

    # Verify signature
    if not verify_signature(raw_body, settings.webhook_secret, x_webhook_signature):
        logger.warning(
            "Invalid signature: provider=%s provided=%s",
            provider, x_webhook_signature,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    
    # Determine the event ID — prefer header, fall back to body field
    event_id = x_webhook_id or _extract_event_id(parsed)
    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event ID (expected X-Webhook-Id header or 'id' in body)",
        )

    # Check for duplicate (idempotency)
    existing = db.execute(
        select(Event).where(
            Event.provider == provider,
            Event.event_id == event_id,
        )
    ).scalar_one_or_none()

    if existing:
        logger.info(
            "Duplicate webhook: provider=%s event_id=%s (existing event db_id=%s)",
            provider, event_id, existing.id,
        )
        return WebhookReceived(
            status="duplicate",
            event_id=event_id,
            message=f"Event {event_id} already received",
        )

    # Save the event
    event = Event(
        provider=provider,
        event_id=event_id,
        event_type=x_webhook_event or parsed.get("type"),
        payload=body_text,
        signature=x_webhook_signature,
        status=EventStatus.PENDING.value,
        attempts=0,
    )

    db.add(event)
    try:
        db.commit()
        db.refresh(event)
    except IntegrityError:
        # Race condition — another request inserted the same event between
        # our SELECT and INSERT. Treat as duplicate.
        db.rollback()
        return WebhookReceived(
            status="duplicate",
            event_id=event_id,
            message=f"Event {event_id} already received",
        )

    logger.info(
        "Received webhook: provider=%s event_id=%s db_id=%s",
        provider, event_id, event.id,
    )

    return WebhookReceived(
        status="accepted",
        event_id=event_id,
        message=f"Event {event_id} queued for processing",
    )


def _extract_event_id(parsed: dict) -> str | None:
    """Try common field names for the event ID."""
    for key in ("id", "event_id", "eventId", "reference"):
        if isinstance(parsed, dict) and key in parsed:
            value = parsed[key]
            if value is not None:
                return str(value)
    return None
@router.get("/events", response_model=list[EventResponse], tags=["debug"])
def list_events(
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """List recent events (for debugging)."""
    stmt = select(Event).order_by(Event.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())