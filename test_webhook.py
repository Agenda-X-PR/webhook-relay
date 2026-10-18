"""Send a test webhook to the running server."""

import hashlib
import hmac
import json
import sys
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000"
SECRET = "change-me-in-production"  # Must match config.webhook_secret


def sign(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_webhook(provider: str, event_id: str, event_type: str, payload: dict) -> None:
    """Send a signed webhook and print the response."""
    url = f"{BASE_URL}/webhooks/{provider}"
    body = json.dumps(payload).encode()
    signature = sign(body, SECRET)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Id": event_id,
        "X-Webhook-Event": event_type,
        "X-Webhook-Signature": signature,
    }

    print(f"\n→ POST {url}")
    print(f"  X-Webhook-Id: {event_id}")
    print(f"  X-Webhook-Signature: {signature[:16]}...")

    try:
        response = httpx.post(url, headers=headers, content=body, timeout=10)
    except httpx.ConnectError:
        print("❌ Could not connect. Is uvicorn running?")
        sys.exit(1)

    print(f"← {response.status_code}")
    print(f"  {response.text}\n")


if __name__ == "__main__":
    event_id = sys.argv[1] if len(sys.argv) > 1 else f"evt_{uuid.uuid4().hex[:8]}"

    payload = {
        "amount": 5000,
        "reference": "ORDER-1",
        "currency": "NGN",
    }

    print(f"Using event ID: {event_id}")
    send_webhook("alatpay", event_id, "payment.success", payload)