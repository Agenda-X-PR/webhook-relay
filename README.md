# Webhook Relay

[![CI](https://github.com/Agenda-X-PR/webhook-relay/actions/workflows/ci.yml/badge.svg)](https://github.com/Agenda-X-PR/webhook-relay/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)

A reliable webhook receiver for payment providers (ALATPay, Flutterwave, Paystack) with signature verification, idempotency, and automatic retries.

## Why This Exists

Webhooks fail. Constantly. Servers go down, networks drop, providers retry, duplicates arrive. Most integrations handle this poorly and lose money silently.

This service solves the four failure modes that break payment webhooks:

| Failure | Solution |
| :--- | :--- |
| **Server was down** | Store first, process later. Nothing is lost. |
| **Duplicate delivery** | Idempotency check on `(provider, event_id)`. |
| **Fake webhooks** | HMAC-SHA256 signature verification (constant-time comparison). |
| **Processing failed** | Automatic retry with exponential backoff. |

## Features

- 🔐 **HMAC-SHA256 signature verification** with constant-time comparison (timing-attack resistant)
- 🔁 **Idempotency** — same webhook twice is rejected as duplicate
- ⏱️ **Exponential backoff** — 30s, 60s, 120s, 240s, 480s
- 💀 **Dead letter queue** — events stop retrying after max attempts
- 📦 **Multi-provider** — one endpoint per provider (`/webhooks/{provider}`)
- 🧪 **28 unit + integration tests** using pytest + FastAPI TestClient
- 📖 **Auto-generated API docs** at `/docs` (Swagger UI)
- 🐳 **SQLite by default** — swap for Postgres with one env var

## Architecture

```
Provider (ALATPay, etc.)
    │
    │  POST /webhooks/{provider}
    │  X-Webhook-Id, X-Webhook-Signature, X-Webhook-Event
    ▼
┌─────────────────────────────────────────┐
│  FastAPI Endpoint                       │
│  1. Verify signature (HMAC-SHA256)      │
│  2. Check idempotency (provider + id)   │
│  3. Save raw body to DB (status=pending)│
│  4. Return 202 Accepted                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Background Worker (polls every 5s)     │
│  1. Pick up pending/failed events       │
│  2. Process business logic              │
│  3. On success → status=success         │
│  4. On failure → backoff & retry        │
│  5. After max attempts → status=dead    │
└─────────────────────────────────────────┘
```

## Requirements

- Python 3.10+
- pip
- (Optional) Docker for containerized deploy

## Installation

```bash
git clone https://github.com/Agenda-X-PR/webhook-relay.git
cd webhook-relay

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and set your secrets:

```bash
cp .env.example .env
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./webhooks.db` | Database connection string |
| `WEBHOOK_SECRET` | `change-me-in-production` | Shared secret for HMAC signatures |
| `MAX_ATTEMPTS` | `5` | Retries before marking an event dead |
| `BASE_RETRY_DELAY_SECONDS` | `30` | First retry delay (doubles each attempt) |
| `WORKER_POLL_INTERVAL_SECONDS` | `5` | How often the worker checks for due events |

## Running

```bash
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Sending a Test Webhook

```bash
python test_webhook.py evt_test_001
```

Expected response:

```json
{"status": "accepted", "event_id": "evt_test_001", "message": "Event evt_test_001 queued for processing"}
```

Send the same command again → `"status": "duplicate"`.

## API Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/webhooks/{provider}` | Receive a webhook |
| `GET` | `/webhooks/events` | List recent events (debug) |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |

## Testing

```bash
pytest -v
```

Expected output:

```
28 passed in ~1.5s
```

All tests use an isolated test database (`test_webhooks.db`) and clean up after themselves.

## Extending

To add real business logic, edit `process_event()` in `worker.py`:

```python
def process_event(event: Event) -> None:
    payload = json.loads(event.payload)

    # Example: update an order status
    if event.event_type == "payment.success":
        mark_order_paid(payload["orderId"])

    # Example: send a notification
    if event.event_type == "payment.failed":
        notify_customer(payload["customer"]["email"], payload["id"])
```

Raise any exception to trigger the retry mechanism.

## Deployment

### Docker (coming soon)

### Environment

Set `DATABASE_URL` to a Postgres connection string for production:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/webhook_relay"
```

### Security Checklist

Before deploying to production:

- [ ] Change `WEBHOOK_SECRET` to a strong random value (`openssl rand -hex 32`)
- [ ] Use a real database (Postgres, not SQLite)
- [ ] Serve behind HTTPS (never over plain HTTP)
- [ ] Set `MAX_ATTEMPTS` based on your SLA
- [ ] Monitor the `/webhooks/events` endpoint or add metrics
- [ ] Rotate secrets periodically

## Project Structure

```
webhook-relay/
├── config.py              # Settings (pydantic-settings)
├── database.py            # SQLAlchemy engine + session
├── models.py              # Event model + status enum
├── schemas.py             # Pydantic request/response models
├── security.py            # HMAC signature verification
├── worker.py              # Background retry worker
├── main.py                # FastAPI app + lifespan
├── routers/
│   └── webhooks.py        # Webhook receiver endpoints
├── tests/
│   ├── test_security.py   # 11 signature tests
│   ├── test_webhooks.py   # 12 HTTP tests
│   └── test_worker.py     # 5 retry logic tests
├── conftest.py            # Pytest fixtures
├── test_webhook.py        # Manual test script
├── test_fail.py           # Manual failure test
├── check_events.py        # View stored events
└── requirements.txt
```

## License

MIT — see [LICENSE](LICENSE) for details.