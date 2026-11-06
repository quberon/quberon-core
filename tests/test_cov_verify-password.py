"""Coverage for app/main.py:verify_password().

verify_password is the login credential check (app/main.py:75-81, called
only from the /auth/login handler at app/main.py:376 with the stored
hash from the users table). No existing test named it: test_app.py
exercises it only indirectly through successful/failed HTTP logins.

Stored format produced by hash_password (app/main.py:69-72):
    pbkdf2_sha256$260000$<base64 16-byte salt>$<base64 derived key>
where the key is PBKDF2-HMAC-SHA256(password UTF-8, salt, rounds).

These tests build stored values independently (hashlib/base64 directly,
low round counts for speed), so a change in algorithm, encoding, field
order, round handling, or comparison in verify_password fails here.
One round-trip test uses the real hash_password at its real 260000
rounds. Malformed-input tests pin the fail-closed contract: any
unparseable stored value (or non-str input) returns False, never raises
-- the login handler depends on that to return 401, not 500.
"""
import base64
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.main import hash_password, verify_password

PASSWORD = "correct horse battery staple"
SALT = bytes(range(16))
OTHER_SALT = bytes(range(16, 32))


def make_stored(password=PASSWORD, rounds=1000, salt=SALT,
                prefix="pbkdf2_sha256"):
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    return "{}${}${}${}".format(
        prefix, rounds,
        base64.b64encode(salt).decode(),
        base64.b64encode(dk).decode(),
    )


# --- Correct / incorrect credentials -------------------------------------

def test_verify_password_accepts_correct_password():
    assert verify_password(PASSWORD, make_stored()) is True


def test_verify_password_rejects_wrong_password():
    assert verify_password("wrong horse battery staple",
                           make_stored()) is False


def test_verify_password_is_case_sensitive():
    assert verify_password(PASSWORD.upper(), make_stored()) is False
    assert verify_password(PASSWORD.capitalize(), make_stored()) is False


def test_verify_password_does_not_trim_whitespace():
    stored = make_stored(password=" padded ")
    assert verify_password(" padded ", stored) is True
    assert verify_password("padded", stored) is False
    assert verify_password(" padded", stored) is False


def test_verify_password_empty_password():
    assert verify_password("", make_stored(password="")) is True
    assert verify_password("", make_stored()) is False
    assert verify_password(PASSWORD, make_stored(password="")) is False


def test_verify_password_unicode_password_utf8():
    pw = "pässwörd-🔑-stopp"
    assert verify_password(pw, make_stored(password=pw)) is True
    assert verify_password("pässwörd-🔑-stopq", make_stored(password=pw)) is False


def test_verify_password_long_password():
    pw = "a" * 10000
    assert verify_password(pw, make_stored(password=pw)) is True
    assert verify_password(pw + "a", make_stored(password=pw)) is False


# --- Round-trip with the real hash_password (260000 rounds) --------------

def test_verify_password_roundtrip_hash_password():
    stored = hash_password("operator-password-123")
    assert stored.startswith("pbkdf2_sha256$260000$")
    assert verify_password("operator-password-123", stored) is True
    assert verify_password("operator-password-124", stored) is False
    assert verify_password("", stored) is False


def test_verify_password_roundtrip_hash_password_random_salt():
    # hash_password salts randomly: two hashes of one password differ as
    # strings, and verify_password must accept both (it reads the salt
    # from the stored value, it does not assume a fixed salt).
    first = hash_password("same-password-123")
    second = hash_password("same-password-123")
    assert first != second
    assert verify_password("same-password-123", first) is True
    assert verify_password("same-password-123", second) is True


# --- Stored fields are actually honoured ---------------------------------

def test_verify_password_uses_stored_round_count():
    # Rewriting only the rounds field must fail: the derived key in the
    # stored value was computed at 1000 rounds, not 1001 or 999.
    stored = make_stored(rounds=1000)
    assert verify_password(PASSWORD, stored.replace("$1000$", "$1001$")) is False
    assert verify_password(PASSWORD, stored.replace("$1000$", "$999$")) is False
    # And a key genuinely derived at a different count verifies.
    assert verify_password(PASSWORD, make_stored(rounds=1)) is True
    assert verify_password(PASSWORD, make_stored(rounds=5000)) is True


def test_verify_password_uses_stored_salt():
    # Key derived with SALT but stored claiming OTHER_SALT must fail.
    dk = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 1000)
    mismatched = "pbkdf2_sha256$1000${}${}".format(
        base64.b64encode(OTHER_SALT).decode(),
        base64.b64encode(dk).decode(),
    )
    assert verify_password(PASSWORD, mismatched) is False
    assert verify_password(PASSWORD, make_stored(salt=OTHER_SALT)) is True


def test_verify_password_rejects_tampered_derived_key():
    stored = make_stored()
    head, dk_b64 = stored.rsplit("$", 1)
    raw = bytearray(base64.b64decode(dk_b64))
    raw[0] ^= 0xFF
    tampered = head + "$" + base64.b64encode(bytes(raw)).decode()
    assert verify_password(PASSWORD, tampered) is False


def test_verify_password_rejects_truncated_or_extended_key():
    stored = make_stored()
    head, dk_b64 = stored.rsplit("$", 1)
    raw = base64.b64decode(dk_b64)
    short = head + "$" + base64.b64encode(raw[:-1]).decode()
    longer = head + "$" + base64.b64encode(raw + b"\x00").decode()
    assert verify_password(PASSWORD, short) is False
    assert verify_password(PASSWORD, longer) is False
    assert verify_password(PASSWORD, stored + "$extra") is False
    assert verify_password(PASSWORD, head + "$") is False


# --- Malformed stored values fail closed (False, never raise) ------------

MALFORMED_STORED = [
    "",                                          # empty
    "nonsense",                                  # no separators
    "pbkdf2_sha256",                             # one field
    "pbkdf2_sha256$260000",                      # two fields
    "pbkdf2_sha256$260000$c2FsdA==",             # three fields
    "pbkdf2_sha256$abc$c2FsdA==$AAAA",           # non-integer rounds
    "pbkdf2_sha256$1000.0$c2FsdA==$AAAA",        # float rounds
    "pbkdf2_sha256$0$c2FsdA==$AAAA",             # zero rounds
    "pbkdf2_sha256$-1$c2FsdA==$AAAA",            # negative rounds
    "pbkdf2_sha256$1000$A$AAAA",                 # bad base64 padding (salt)
    "pbkdf2_sha256$1000$!!!not-b64!!!$AAAA",     # salt decodes empty/garbage
    "pbkdf2_sha256$1000$c2FsdA==$not-a-key",     # key is not the derived key
    "$$$",
    "$$$$",
]


@pytest.mark.parametrize("stored", MALFORMED_STORED)
def test_verify_password_malformed_stored_returns_false(stored):
    assert verify_password(PASSWORD, stored) is False


@pytest.mark.parametrize("bad_stored", [None, 123, b"pbkdf2_sha256$1$AA$AA",
                                        ["pbkdf2_sha256$1$AA$AA"]])
def test_verify_password_non_str_stored_returns_false(bad_stored):
    # Signature says str, but the broad except in verify_password makes
    # non-str stored values fail closed instead of raising -- pin that,
    # because the login handler has no other guard before this call.
    assert verify_password(PASSWORD, bad_stored) is False


@pytest.mark.parametrize("bad_password", [None, 123, b"password"])
def test_verify_password_non_str_password_returns_false(bad_password):
    assert verify_password(bad_password, make_stored()) is False


def test_verify_password_result_is_bool():
    assert type(verify_password(PASSWORD, make_stored())) is bool
    assert type(verify_password("nope", make_stored())) is bool
    assert type(verify_password(PASSWORD, "garbage")) is bool


# --- Characterization: known gaps, pinned so a fix is a visible change ---

def test_verify_password_ignores_scheme_prefix_characterization():
    # CHARACTERIZATION, not a desired contract: verify_password unpacks
    # stored.split("$", 3) and discards the first field, so the
    # "pbkdf2_sha256" scheme label is never checked. A stored value with
    # any (or no) prefix verifies if rounds/salt/key match. If a fix
    # validates the prefix, update this test deliberately -- and note
    # the login path would then reject any legacy non-conforming rows.
    assert verify_password(PASSWORD, make_stored(prefix="anything")) is True
    assert verify_password(PASSWORD, make_stored(prefix="")) is True
    assert verify_password(PASSWORD, make_stored()) is True
