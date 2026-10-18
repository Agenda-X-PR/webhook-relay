"""Send a webhook with a broken signature to test rejection."""

import httpx

url = "http://127.0.0.1:8000/webhooks/alatpay"
headers = {
    "Content-Type": "application/json",
    "X-Webhook-Id": "evt_fake",
    "X-Webhook-Signature": "0" * 64,  # obviously wrong
}

response = httpx.post(url, headers=headers, json={"amount": 999999}, timeout=10)
print(f"← {response.status_code}")
print(f"  {response.text}")