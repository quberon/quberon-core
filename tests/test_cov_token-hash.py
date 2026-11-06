"""Coverage for app/main.py:token_hash().

token_hash is the session-table key (app/main.py Store.create_session /
get_session / delete_session): the raw session token is never stored,
only token_hash(token). These tests pin the function itself with
independently known SHA-256 answers -- not values recomputed with
hashlib at test time, which could not catch an algorithm/encoding
change -- and then verify the Store-level consequence.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.main import Store, token_hash

# SHA-256 (UTF-8 encoding) known answers. "", "abc" and the 10000x"a"
# input are the standard published vectors; the rest were computed once
# from the specification and are hardcoded here so a change of digest,
# encoding, salting, truncation or case in token_hash fails the test.
KNOWN = [
    ("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ("abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    ("hello world", "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"),
    ("operator-password-123", "1de8ac7f58d49839a68a41d5d417d1276c4f5ba613ff966c3e7e5910613abb14"),
    # Non-ASCII: pins .encode() to UTF-8 (not latin-1 / utf-16).
    ("stopp-å-✓", "662f2ed2beb4fa93933bd76db7148a26243b162d5f655e1a190f3f98d0fa2b8a"),
    # Embedded NUL must be hashed, not treated as a terminator.
    ("abc\x00", "dc1114cd074914bd872cc1f9a23ec910ea2203bc79779ab2e17da25782a624fc"),
    ("a" * 10000, "27dd1f61b867b6a0f6e9d8a41c43231de52107e53ae424de8f847b821db4b711"),
]


@pytest.mark.parametrize("token,expected", KNOWN)
def test_token_hash_known_answer(token, expected):
    assert token_hash(token) == expected


def test_token_hash_format_is_64_lowercase_hex():
    for token, _ in KNOWN:
        digest = token_hash(token)
        assert isinstance(digest, str)
        assert len(digest) == 64
        assert digest == digest.lower()
        assert all(c in "0123456789abcdef" for c in digest)
        int(digest, 16)  # parses as hex


def test_token_hash_is_deterministic_and_unsalted():
    # A random salt (as in hash_password) would break session lookup:
    # create_session stores one value, get_session recomputes it.
    token = "some-session-token"
    assert token_hash(token) == token_hash(token) == token_hash(str(token))


def test_token_hash_distinguishes_near_identical_tokens():
    tokens = ["abc", "ABC", "abc ", " abc", "abc\x00", "abd", "abc\n", ""]
    digests = [token_hash(t) for t in tokens]
    assert len(set(digests)) == len(tokens)


def test_token_hash_output_does_not_contain_raw_token():
    token = "a-recognisable-raw-session-token-value"
    digest = token_hash(token)
    assert digest != token
    assert token not in digest


@pytest.mark.parametrize("bad", [None, b"abc", 123, ["abc"]])
def test_token_hash_rejects_non_str(bad):
    # Current contract is str-only: .encode() raises AttributeError.
    # (If a deliberate TypeError-raising guard is added later, update
    # this test -- do not silently accept bytes, which would hash
    # differently at session creation vs. lookup.)
    with pytest.raises(AttributeError):
        token_hash(bad)


def test_store_stores_only_token_hash_and_looks_up_by_it(tmp_path):
    db = str(tmp_path / "sessions.db")
    store = Store(db)
    # get_session JOINs users, so the session owner must exist.
    store.create_user("operator1", "operator-password-123", "operator")
    token, _csrf = store.create_session("operator1")

    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT token_hash, username FROM sessions").fetchall()
    assert rows == [(token_hash(token), "operator1")]
    assert rows[0][0] != token

    # Lookup recomputes token_hash: exact token finds the session,
    # any other token (hence any other hash) does not.
    row = store.get_session(token)
    assert row is not None and row["username"] == "operator1"
    assert store.get_session(token + "x") is None
    assert store.get_session("") is None
    assert store.get_session(None) is None

    store.delete_session(token)
    assert store.get_session(token) is None
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
