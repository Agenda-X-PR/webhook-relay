"""Integration tests for the webhook receiver endpoints."""

import hashlib
import hmac
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from config import settings
from main import app


SECRET = settings.webhook_secret


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def _sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def _unique_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:8]}"


# ---------- health & root ----------

def test_root_returns_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_returns_healthy(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ---------- happy path ----------

def test_receive_valid_webhook_returns_202(client):
    event_id = _unique_event_id()
    body = json.dumps({"amount": 5000, "reference": "ORDER-1"}).encode()

    r = client.post(
        "/webhooks/alatpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Id": event_id,
            "X-Webhook-Event": "payment.success",
            "X-Webhook-Signature": _sign(body),
        },
    )

    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "accepted"
    assert data["event_id"] == event_id


def test_duplicate_webhook_returns_duplicate_status(client):
    event_id = _unique_event_id()
    body = json.dumps({"amount": 100}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Id": event_id,
        "X-Webhook-Signature": _sign(body),
    }

    first = client.post("/webhooks/alatpay", content=body, headers=headers)
    assert first.status_code == 202
    assert first.json()["status"] == "accepted"

    second = client.post("/webhooks/alatpay", content=body, headers=headers)
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"


def test_different_providers_with_same_event_id_both_accepted(client):
    event_id = _unique_event_id()
    body = json.dumps({"amount": 100}).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Id": event_id,
        "X-Webhook-Signature": _sign(body),
    }

    r1 = client.post("/webhooks/alatpay", content=body, headers=headers)
    r2 = client.post("/webhooks/flutterwave", content=body, headers=headers)

    assert r1.json()["status"] == "accepted"
    assert r2.json()["status"] == "accepted"


# ---------- security ----------

def test_missing_signature_returns_401(client):
    body = json.dumps({"amount": 100}).encode()
    r = client.post(
        "/webhooks/alatpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Id": _unique_event_id(),
        },
    )
    assert r.status_code == 401
    assert "signature" in r.json()["detail"].lower()


def test_bad_signature_returns_401(client):
    body = json.dumps({"amount": 100}).encode()
    r = client.post(
        "/webhooks/alatpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Id": _unique_event_id(),
            "X-Webhook-Signature": "0" * 64,
        },
    )
    assert r.status_code == 401


def test_tampered_body_returns_401(client):
    original = json.dumps({"amount": 100}).encode()
    tampered = json.dumps({"amount": 9999}).encode()

    r = client.post(
        "/webhooks/alatpay",
        content=tampered,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Id": _unique_event_id(),
            "X-Webhook-Signature": _sign(original),
        },
    )
    assert r.status_code == 401


# ---------- validation ----------

def test_missing_event_id_returns_400(client):
    body = json.dumps({"amount": 100}).encode()
    r = client.post(
        "/webhooks/alatpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": _sign(body),
        },
    )
    assert r.status_code == 400
    assert "event" in r.json()["detail"].lower()


def test_event_id_falls_back_to_body(client):
    event_id = _unique_event_id()
    body = json.dumps({"id": event_id, "amount": 100}).encode()

    r = client.post(
        "/webhooks/alatpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": _sign(body),
        },
    )
    assert r.status_code == 202
    assert r.json()["event_id"] == event_id


def test_invalid_json_returns_400(client):
    body = b"not-json{{"
    r = client.post(
        "/webhooks/alatpay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Id": _unique_event_id(),
            "X-Webhook-Signature": _sign(body),
        },
    )
    assert r.status_code == 400


# ---------- listing ----------

def test_list_events_returns_array(client):
    r = client.get("/webhooks/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)