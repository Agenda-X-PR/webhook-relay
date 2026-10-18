"""Database models for the webhook relay."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class EventStatus(str, Enum):
    """Lifecycle states for a webhook event."""

    PENDING = "pending"           # Received, not yet processed
    PROCESSING = "processing"     # Currently being processed
    SUCCESS = "success"           # Processed successfully
    FAILED = "failed"             # Failed but will retry
    DEAD = "dead"                 # Gave up after max_attempts


class Event(Base):
    """A single webhook event received from a provider."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Provider identification (e.g., "alatpay", "flutterwave")
    provider: Mapped[str] = mapped_column(String(64), index=True)

    # Unique event ID from the provider — used for idempotency
    event_id: Mapped[str] = mapped_column(String(128), index=True)

    # Optional event type (e.g., "payment.success")
    event_type: Mapped[str] = mapped_column(String(128), nullable=True)

    # Raw JSON payload as received
    payload: Mapped[str] = mapped_column(Text)

    # Signature header received with the request
    signature: Mapped[str] = mapped_column(String(256), nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(
        String(16), default=EventStatus.PENDING.value, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Event id={self.id} provider={self.provider} "
            f"event_id={self.event_id} status={self.status} "
            f"attempts={self.attempts}>"
        )