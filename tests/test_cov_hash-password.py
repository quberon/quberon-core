"""Direct coverage for app.main.hash_password (previously only exercised
indirectly via Store.create_user / login flows in tests/test_app.py).

Contract pinned from app/main.py:69-72:
  hash_password(password: str) -> str
  returns "pbkdf2_sha256$260000$<b64 16-byte salt>$<b64 32-byte dk>"
  where dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)

Tests recompute the derived key independently instead of mocking
secrets/hashlib, so they fail if the algorithm, iteration count,
encoding, salt size, or output format drifts.
"""
import base64
import binascii
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import hash_password, verify_password

ROUNDS = 260_000


def _parse(stored):
    assert isinstance(stored, str)
    parts = stored.split("$")
    assert len(parts) == 4, stored
    scheme, rounds, salt_b64, dk_b64 = parts
    # validate=True: reject non-base64 alphabets / bad padding rather
    # than silently ignoring invalid characters.
    salt = base64.b64decode(salt_b64, validate=True)
    dk = base64.b64decode(dk_b64, validate=True)
    return scheme, rounds, salt, dk, salt_b64, dk_b64


def _recomputed_dk(password, salt, rounds=ROUNDS):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)


def test_hash_password_format_scheme_rounds_and_lengths():
    scheme, rounds, salt, dk, salt_b64, dk_b64 = _parse(hash_password("correct horse battery staple"))
    assert scheme == "pbkdf2_sha256"
    assert rounds == "260000"
    assert int(rounds) == ROUNDS
    assert len(salt) == 16
    assert len(dk) == 32  # SHA-256 output size
    # Canonical base64: re-encoding the decoded bytes reproduces the fields.
    assert base64.b64encode(salt).decode() == salt_b64
    assert base64.b64encode(dk).decode() == dk_b64


def test_hash_password_derived_key_matches_independent_pbkdf2():
    for password in ("a", "operator-password-123", "p@ss;word$with$dollars"):
        _, _, salt, dk, _, _ = _parse(hash_password(password))
        assert dk == _recomputed_dk(password, salt)
        # A different password must not produce the stored derived key.
        assert dk != _recomputed_dk(password + "!", salt)


def test_hash_password_empty_password_is_hashed_not_rejected():
    _, _, salt, dk, _, _ = _parse(hash_password(""))
    assert dk == _recomputed_dk("", salt)


def test_hash_password_unicode_password_uses_utf8_encoding():
    password = "lösenord-åäö-🔐"
    _, _, salt, dk, _, _ = _parse(hash_password(password))
    assert dk == hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ROUNDS)
    assert dk != hashlib.pbkdf2_hmac("sha256", password.encode("latin-1", "ignore"), salt, ROUNDS)


def test_hash_password_long_password():
    password = "x" * 4096
    _, _, salt, dk, _, _ = _parse(hash_password(password))
    assert dk == _recomputed_dk(password, salt)


def test_hash_password_random_salt_makes_same_password_hash_differently():
    password = "same-password-123"
    first = hash_password(password)
    second = hash_password(password)
    assert first != second
    _, _, salt1, dk1, _, _ = _parse(first)
    _, _, salt2, dk2, _, _ = _parse(second)
    assert salt1 != salt2
    # Both are nevertheless valid hashes of the same password.
    assert dk1 == _recomputed_dk(password, salt1)
    assert dk2 == _recomputed_dk(password, salt2)


def test_hash_password_output_does_not_contain_plaintext():
    password = "distinctive-plaintext-marker-123"
    stored = hash_password(password)
    assert password not in stored
    assert stored != password


def test_hash_password_roundtrips_through_verify_password():
    stored = hash_password("roundtrip-password-123")
    assert verify_password("roundtrip-password-123", stored) is True
    assert verify_password("roundtrip-password-124", stored) is False
    assert verify_password("", stored) is False


def test_hash_password_tampered_derived_key_does_not_verify():
    scheme, rounds, salt, dk, _, _ = _parse(hash_password("tamper-password-123"))
    tampered_dk = bytes([dk[0] ^ 0x01]) + dk[1:]
    tampered = "$".join(
        (scheme, rounds, base64.b64encode(salt).decode(), base64.b64encode(tampered_dk).decode())
    )
    assert tampered_dk != _recomputed_dk("tamper-password-123", salt)
    assert verify_password("tamper-password-123", tampered) is False


def test_hash_password_fields_are_strict_base64():
    # Guards the parser assumption used above: fields emitted by
    # hash_password must decode under strict validation (no whitespace
    # or off-alphabet characters that lenient decoders would skip).
    _, _, salt_b64, dk_b64 = hash_password("strict-b64-password").split("$")
    try:
        base64.b64decode(salt_b64, validate=True)
        base64.b64decode(dk_b64, validate=True)
    except (binascii.Error, ValueError) as exc:  # pragma: no cover
        raise AssertionError(f"hash_password emitted non-strict-base64 field: {exc}") from exc
