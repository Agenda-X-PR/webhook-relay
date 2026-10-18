"""Send a webhook that will fail processing, to test retry."""

import hashlib
import hmac
import json
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"
SECRET = "change-me-in-production"


def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


payload = {"simulate_failure": True, "amount": 1000}
body = json.dumps(payload).encode()
event_id = sys.argv[1] if len(sys.argv) > 1 else "evt_fail_001"

headers = {
    "Content-Type": "application/json",
    "X-Webhook-Id": event_id,
    "X-Webhook-Event": "payment.failed",
    "X-Webhook-Signature": sign(body),
}

response = httpx.post(f"http://127.0.0.1:8000/webhooks/alatpay",
                     headers=headers, content=body, timeout=10)
print(f"← {response.status_code}")
print(f"  {response.text}")