"""Tests for webhook signature verification."""

from security import compute_signature, verify_signature


# ---------- compute_signature ----------

def test_compute_signature_returns_hex_string():
    sig = compute_signature(b'{"test":1}', "secret")
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA256 hex digest is 64 characters
    assert all(c in "0123456789abcdef" for c in sig)


def test_compute_signature_is_deterministic():
    body = b"same body"
    assert compute_signature(body, "secret") == compute_signature(body, "secret")


def test_compute_signature_differs_for_different_bodies():
    assert compute_signature(b"body1", "secret") != compute_signature(b"body2", "secret")


def test_compute_signature_differs_for_different_secrets():
    assert compute_signature(b"same", "secret1") != compute_signature(b"same", "secret2")


# ---------- verify_signature ----------

def test_verify_accepts_valid_signature():
    body = b'{"amount":100}'
    sig = compute_signature(body, "secret")
    assert verify_signature(body, "secret", sig) is True


def test_verify_rejects_wrong_secret():
    body = b'{"amount":100}'
    sig = compute_signature(body, "secret")
    assert verify_signature(body, "wrong-secret", sig) is False


def test_verify_rejects_tampered_body():
    body = b'{"amount":100}'
    sig = compute_signature(body, "secret")
    tampered = b'{"amount":1000}'
    assert verify_signature(tampered, "secret", sig) is False


def test_verify_rejects_none_signature():
    assert verify_signature(b"body", "secret", None) is False


def test_verify_rejects_empty_signature():
    assert verify_signature(b"body", "secret", "") is False


def test_verify_is_case_insensitive():
    body = b'{"x":1}'
    sig = compute_signature(body, "secret")
    assert verify_signature(body, "secret", sig.upper()) is True


def test_verify_strips_surrounding_whitespace():
    body = b'{"x":1}'
    sig = compute_signature(body, "secret")
    assert verify_signature(body, "secret", f"  {sig}  ") is True