"""Tests for the background retry worker."""

import json
from datetime import datetime, timedelta

import pytest

from config import settings
from database import SessionLocal
from models import Event, EventStatus
from worker import process_due_events_once


def _create_event(event_id: str, payload: dict) -> int:
    """Insert a pending event into the test DB and return its id."""
    db = SessionLocal()
    try:
        event = Event(
            provider="alatpay",
            event_id=event_id,
            event_type="payment.test",
            payload=json.dumps(payload),
            status=EventStatus.PENDING.value,
            attempts=0,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.id
    finally:
        db.close()


def _get_event(event_id: str) -> Event | None:
    db = SessionLocal()
    try:
        return db.query(Event).filter(Event.event_id == event_id).first()
    finally:
        db.close()


# ---------- success path ----------

def test_successful_event_marked_success():
    _create_event("evt_w1", {"amount": 100})
    processed = process_due_events_once()
    assert processed == 1

    event = _get_event("evt_w1")
    assert event.status == EventStatus.SUCCESS.value
    assert event.attempts == 0
    assert event.processed_at is not None


# ---------- failure path ----------

def test_failing_event_marked_failed_with_backoff():
    _create_event("evt_w2", {"simulate_failure": True})
    process_due_events_once()

    event = _get_event("evt_w2")
    assert event.status == EventStatus.FAILED.value
    assert event.attempts == 1
    assert event.next_retry_at is not None
    assert event.next_retry_at > datetime.utcnow()


def test_event_moves_to_dead_after_max_attempts():
    _create_event("evt_w3", {"simulate_failure": True})

    # Force it to max_attempts - 1 already done
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.event_id == "evt_w3").first()
        event.attempts = settings.max_attempts - 1
        event.status = EventStatus.FAILED.value
        event.next_retry_at = None  # due now
        db.commit()
    finally:
        db.close()

    process_due_events_once()

    event = _get_event("evt_w3")
    assert event.status == EventStatus.DEAD.value
    assert event.attempts == settings.max_attempts


# ---------- retry gating ----------

def test_future_retry_not_processed():
    db = SessionLocal()
    try:
        event = Event(
            provider="alatpay",
            event_id="evt_w4",
            payload=json.dumps({"amount": 100}),
            status=EventStatus.FAILED.value,
            attempts=1,
            next_retry_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(event)
        db.commit()
    finally:
        db.close()

    processed = process_due_events_once()
    assert processed == 0

    event = _get_event("evt_w4")
    assert event.status == EventStatus.FAILED.value  # unchanged


def test_success_events_not_reprocessed():
    _create_event("evt_w5", {"amount": 100})
    process_due_events_once()

    # Run again — nothing should process
    processed = process_due_events_once()
    assert processed == 0