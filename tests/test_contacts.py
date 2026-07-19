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
            "=?UTF-8?Q?Guerra=2c_Ges=c3=b9?=",
            "gesuguerra1990@gmail.com",
            "guerra_gesù",
        ),
        (
            "=?utf-8?Q?Niccol=C3=B2_Benetollo?=",
            "nicobenetollo@hotmail.it",
            "niccolò_benetollo",
        ),
        (
            "=?UTF-8?Q?Nicol=c3=b2_Meschini?=",
            "meschini.nico@gmail.com",
            "nicolò_meschini",
        ),
        (
            "=?UTF-8?Q?Elisaveta=20Cucu?=",
            "elisaveta.cucu@enerviva.it",
            "elisaveta_cucu",
        ),
        (
            "=?UTF-8?Q?Jean=2DFran=C3=A7ois_Fiset?=",
            "jeff@parabole.ca",
            "jean_françois_fiset",
        ),
        # iso‑8859‑1 charset
        (
            "=?iso-8859-1?Q?nicol=F2?=",
            "valentina.n87@gmail.com",
            "nicolò",
        ),
        (
            "=?ISO-8859-1?Q?=C9quipe_Google=2B?=",
            "noreply-475ba29f@plus.google.com",
            "équipe_google",
        ),
        # Base‑64 (B) encoding
        (
            "=?UTF-8?B?SW5mbyBCb25Cb2FyZA==?=",
            "info98464+ims@indeedemail.com",
            "info_bonboard",
        ),
        (
            "=?UTF-8?B?QkFSQUtVREEwNyBCQVJBS1VEQTA3?=",
            "tabuhovr@mail.ru",
            "barakuda07_barakuda07",
        ),
        # KOI8‑R (Cyrillic)
        (
            "=?KOI8-R?B?9MnN1dIg9MHP1w==?=",
            "timurtaov@mail.ru",
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
        ('"Maria Lea', "maria.lea@test.com", "maria_lea"),
        ('"TAOV', "nasir.taov@gmail.com", "taov"),
        ('"Guaitini', "guaitini@example.com", "guaitini"),
        ("  Bandirali Ivana  ", "ivana.bandirali@iulm.it", "bandirali_ivana"),
    ],
)
def test_quotes_and_whitespace(name: str, email: str, expected: str) -> None:
    """Leading quotes and surrounding whitespace are removed."""
    assert _normalize_id(name, email) == expected


# ── Special characters → underscore ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("Pipparoni Giulio", "giulio.1993@live.it", "pipparoni_giulio"),
        ("f@oval-money.intercom-mail.com", "", "f_oval_money_intercom_mail_com"),
        ("Undisclosed recipients:;", "undisclosed recipients:;", "undisclosed_recipients"),
    ],
)
def test_special_chars_to_underscore(name: str, email: str, expected: str) -> None:
    """At‑signs, commas, colons, semicolons and other non‑word chars become underscores."""
    assert _normalize_id(name, email) == expected


# ── Consecutive underscores collapsed ─────────────────────────────────────────


def test_collapses_multiple_underscores() -> None:
    """Runs of non‑word chars collapse to a single underscore, no leading/trailing."""
    assert _normalize_id(",,,Hello!!!World...", "h@x.com") == "hello_world"


# ── Empty / missing name falls back to email local part ───────────────────────


@pytest.mark.parametrize(
    ("name", "email", "expected"),
    [
        ("", "alice@example.com", "alice"),
        ("   ", "bob.smith@domain.org", "bob.smith"),
    ],
)
def test_empty_name_falls_back(name: str, email: str, expected: str) -> None:
    """When the display name is blank, derive the ID from the email local‑part."""
    assert _normalize_id(name, email) == expected


# ── Already‑clean names pass through ──────────────────────────────────────────


def test_already_clean_is_idempotent() -> None:
    """Names that already look like clean IDs stay the same."""
    assert _normalize_id("alice_wonderland", "alice@x.com") == "alice_wonderland"
