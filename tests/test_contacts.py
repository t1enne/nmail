"""Tests for src/nmail/cli/contacts.py — contact ID normalization."""

from __future__ import annotations

import pytest

from nmail.cli.contacts import _normalize_id


# ── MIME-encoded word decoding ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        # Quoted‑Printable (Q) encoding
        (
            "=?UTF-8?Q?Rossi=2c_Mar=c3=b2?=",
            "rossi.marco@example.com",
            "rossi_marò",
        ),
        (
            "=?utf-8?Q?Fran=C3=A7ois_Dupont?=",
            "dupont.francois@example.com",
            "françois_dupont",
        ),
        (
            "=?UTF-8?Q?Jos=c3=a9_Garc=c3=ada?=",
            "garcia.jose@example.com",
            "josé_garcía",
        ),
        (
            "=?UTF-8?Q?Anna=20Bianchi?=",
            "bianchi.anna@example.com",
            "anna_bianchi",
        ),
        (
            "=?UTF-8?Q?Jean=2DPierre_Dubois?=",
            "dubois@example.com",
            "jean_pierre_dubois",
        ),
        # iso‑8859‑1 charset
        (
            "=?iso-8859-1?Q?andr=E8?=",
            "andre@example.com",
            "andrè",
        ),
        (
            "=?ISO-8859-1?Q?=C9quipe_Support=2B?=",
            "noreply-support@example.com",
            "équipe_support",
        ),
        # Base‑64 (B) encoding
        (
            "=?UTF-8?B?Sm9obiBEb2U=?=",
            "john.doe@example.com",
            "john_doe",
        ),
        (
            "=?UTF-8?B?SEVMTE9XT1JMRCBIRUxMT1dPUkxE?=",
            "hello@example.com",
            "helloworld_helloworld",
        ),
        # KOI8‑R (Cyrillic)
        (
            "=?KOI8-R?B?9MnN1dIg9MHP1w==?=",
            "ivan@example.com",
            "тимур_таов",
        ),
    ],
)
def test_mime_decoded(name: str, email: str, expected: str) -> None:
    """MIME-encoded display names are decoded before normalising."""
    assert _normalize_id(name, email) == expected


# ── Quotes and whitespace stripping ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ('"Maria Lea', "maria.lea@example.com", "maria_lea"),
        ('"SMITH', "john.smith@example.com", "smith"),
        ('"Guaitini', "guaitini@example.com", "guaitini"),
        ("  Bond James  ", "james.bond@example.com", "bond_james"),
    ],
)
def test_quotes_and_whitespace(name: str, email: str, expected: str) -> None:
    """Leading quotes and surrounding whitespace are removed."""
    assert _normalize_id(name, email) == expected


# ── Special characters → underscore ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("Verdi Luigi", "luigi.verdi@example.com", "verdi_luigi"),
        ("f@example.com", "", "f_example_com"),
        ("Undisclosed recipients:;", "undisclosed recipients:;", "undisclosed_recipients"),
    ],
)
def test_special_chars_to_underscore(name: str, email: str, expected: str) -> None:
    """At‑signs, commas, colons, semicolons and other non‑word chars become underscores."""
    assert _normalize_id(name, email) == expected


# ── Consecutive underscores collapsed ─────────────────────────────────────────


def test_collapses_multiple_underscores() -> None:
    """Runs of non‑word chars collapse to a single underscore, no leading/trailing."""
    assert _normalize_id(",,,Hello!!!World...", "h@example.com") == "hello_world"


# ── Empty / missing name falls back to email local part ───────────────────────


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("", "alice@example.com", "alice"),
        ("   ", "bob.smith@example.com", "bob.smith"),
    ],
)
def test_empty_name_falls_back(name: str, email: str, expected: str) -> None:
    """When the display name is blank, derive the ID from the email local‑part."""
    assert _normalize_id(name, email) == expected


# ── Already‑clean names pass through ──────────────────────────────────────────


def test_already_clean_is_idempotent() -> None:
    """Names that already look like clean IDs stay the same."""
    assert _normalize_id("alice_wonderland", "alice@example.com") == "alice_wonderland"
