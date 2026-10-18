"""Background worker that processes pending webhook events with retries."""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import Event, EventStatus

logger = logging.getLogger(__name__)


def process_event(event: Event) -> None:
    """Process a single webhook event.

    Replace this with your real business logic (e.g., update an order,
    send a notification, credit an account).

    For demo purposes:
    - Raises an exception if payload contains {"simulate_failure": true}
    - Otherwise succeeds
    """
    try:
        payload = json.loads(event.payload) if event.payload else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON payload: {e}")

    if payload.get("simulate_failure"):
        raise RuntimeError("Simulated processing failure")

    logger.info("Processed event id=%s provider=%s event_id=%s",
                event.id, event.provider, event.event_id)


def _get_due_events(db: Session, limit: int = 10) -> list[Event]:
    """Find events that are due for processing."""
    now = datetime.utcnow()
    stmt = (
        select(Event)
        .where(Event.status.in_([EventStatus.PENDING.value, EventStatus.FAILED.value]))
        .where(or_(Event.next_retry_at.is_(None), Event.next_retry_at <= now))
        .order_by(Event.id.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def process_due_events_once() -> int:
    """Process all currently due events. Returns the number processed."""
    db = SessionLocal()
    processed = 0
    try:
        events = _get_due_events(db)
        for event in events:
            event.status = EventStatus.PROCESSING.value
            db.commit()

            try:
                process_event(event)
                event.status = EventStatus.SUCCESS.value
                event.processed_at = datetime.utcnow()
                event.last_error = None
                logger.info("Event %s succeeded", event.id)
            except Exception as e:
                event.attempts += 1
                event.last_error = str(e)

                if event.attempts >= settings.max_attempts:
                    event.status = EventStatus.DEAD.value
                    logger.error(
                        "Event %s moved to DEAD after %d attempts: %s",
                        event.id, event.attempts, e,
                    )
                else:
                    event.status = EventStatus.FAILED.value
                    delay = settings.base_retry_delay_seconds * (2 ** (event.attempts - 1))
                    event.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                    logger.warning(
                        "Event %s failed (attempt %d), retry in %ds: %s",
                        event.id, event.attempts, delay, e,
                    )

            db.commit()
            processed += 1
    finally:
        db.close()
    return processed


async def worker_loop() -> None:
    """Run the worker forever, polling for due events."""
    logger.info("Worker started (poll interval=%ds)",
                settings.worker_poll_interval_seconds)
    while True:
        try:
            processed = await asyncio.to_thread(process_due_events_once)
            if processed:
                logger.info("Worker processed %d event(s)", processed)
        except Exception as e:
            logger.exception("Worker loop error: %s", e)

        await asyncio.sleep(settings.worker_poll_interval_seconds)