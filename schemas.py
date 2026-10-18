"""Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field


class WebhookReceived(BaseModel):
    """Response returned when a webhook is accepted."""

    status: str = Field(..., description="'accepted' or 'duplicate'")
    event_id: str
    message: str


class EventResponse(BaseModel):
    """Full representation of an event for the API."""

    id: int
    provider: str
    event_id: str
    event_type: str | None
    status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}