"""Security utilities for webhook signature verification."""

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def compute_signature(raw_body: bytes, secret: str) -> str:
    """Compute the HMAC-SHA256 signature for a webhook body.

    Args:
        raw_body: The exact request body bytes as received.
        secret:   The shared signing secret.

    Returns:
        Lowercase hex string of the HMAC digest.
    """
    return hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(raw_body: bytes, secret: str, provided_signature: str | None) -> bool:
    """Verify a webhook signature using constant-time comparison.

    Args:
        raw_body:           The exact request body bytes.
        secret:             The shared signing secret.
        provided_signature: The signature header value from the request.

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not provided_signature:
        return False

    expected = compute_signature(raw_body, secret)

    # constant-time comparison prevents timing side-channel attacks
    return hmac.compare_digest(expected, provided_signature.strip().lower())