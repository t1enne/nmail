"""Tests for src/nmail/headers.py — header extraction from Maildir files."""

from __future__ import annotations

from pathlib import Path

import pytest

from nmail.headers import extract_body, extract_header, extract_headers_block


# ── extract_header ───────────────────────────────────────────────────────────


def test_extract_header_simple() -> None:
    f = _write("From: alice@example.com\nTo: bob@example.com\nSubject: Hello\n\nBody")
    assert extract_header(f, "From") == "alice@example.com"
    assert extract_header(f, "To") == "bob@example.com"
    assert extract_header(f, "Subject") == "Hello"


def test_extract_header_case_insensitive() -> None:
    f = _write("from: alice@x.com\nSUBJECT: Test\n\nBody")
    assert extract_header(f, "From") == "alice@x.com"
    assert extract_header(f, "subject") == "Test"


def test_extract_header_not_found() -> None:
    f = _write("From: a\n\nBody")
    assert extract_header(f, "X-Custom") is None


def test_extract_header_folded_value() -> None:
    """RFC2822 folded headers: continuation lines start with space/tab."""
    f = _write(
        "Subject: This is a very long\n"
        " subject line that\n"
        " continues here\n"
        "From: alice@x.com\n"
        "\n"
        "Body"
    )
    result = extract_header(f, "Subject")
    assert result == "This is a very long subject line that continues here"


def test_extract_header_multiple_occurrences_returns_first() -> None:
    f = _write("Received: first\nReceived: second\n\nBody")
    assert extract_header(f, "Received") == "first"


def test_extract_header_stops_at_body() -> None:
    """Headers end at first blank line. Text after blank line isn't parsed as header."""
    f = _write("From: a\n\nTo: this_is_body_not_header\n")
    assert extract_header(f, "To") is None


def test_extract_header_no_colon() -> None:
    f = _write("MalformedLine\nFrom: a\n\nBody")
    assert extract_header(f, "From") == "a"


def test_extract_header_empty_file() -> None:
    f = _write("")
    assert extract_header(f, "Subject") is None


def test_extract_header_with_leading_whitespace_value() -> None:
    f = _write("Subject:   padded value  \n\nBody")
    assert extract_header(f, "Subject") == "padded value"


# ── extract_body ─────────────────────────────────────────────────────────────


def test_extract_body_simple() -> None:
    f = _write("From: a\nTo: b\nSubject: c\n\nHello\nWorld")
    assert extract_body(f) == "Hello\nWorld"


def test_extract_body_single_line() -> None:
    f = _write("From: a\n\nOne line body")
    assert extract_body(f) == "One line body"


def test_extract_body_empty() -> None:
    f = _write("From: a\n\n")
    assert extract_body(f) == ""


def test_extract_body_no_headers() -> None:
    f = _write("\n\nBody only")
    # "Body only" is after second blank line
    assert extract_body(f) == "Body only"


def test_extract_body_only_blank_lines() -> None:
    f = _write("")
    assert extract_body(f) == ""


def test_extract_body_with_multiple_blank_lines_in_body() -> None:
    f = _write("From: a\n\nLine 1\n\nLine 2\n\nLine 3")
    # Only splits on first blank line
    assert "Line 1" in extract_body(f)
    assert "Line 2" in extract_body(f)
    assert "Line 3" in extract_body(f)


# ── extract_headers_block ───────────────────────────────────────────────────


def test_extract_headers_block() -> None:
    f = _write("From: a\nTo: b\nSubject: c\n\nBody here")
    block = extract_headers_block(f)
    assert "From: a" in block
    assert "To: b" in block
    assert "Subject: c" in block
    assert "Body" not in block


def test_extract_headers_block_no_body() -> None:
    f = _write("From: a\nTo: b")
    hb = extract_headers_block(f)
    assert "From: a" in hb


def test_extract_headers_block_empty() -> None:
    f = _write("")
    assert extract_headers_block(f) == ""


# ── extract_header: special characters ───────────────────────────────────────


def test_extract_header_with_email_addresses() -> None:
    f = _write('From: "Alice Example" <alice@example.com>\n\nBody')
    assert extract_header(f, "From") == '"Alice Example" <alice@example.com>'


def test_extract_header_message_id() -> None:
    f = _write("Message-ID: <abc123@mail.example.com>\n\nBody")
    assert extract_header(f, "Message-ID") == "<abc123@mail.example.com>"


# ── helpers ──────────────────────────────────────────────────────────────────


def _write(content: str) -> Path:
    p = Path(f"test_hdr_{hash(content) & 0xFFFF}.txt")
    p.write_text(content)
    return p


@pytest.fixture(autouse=True)
def _cleanup() -> None:
    yield
    import glob

    for f in glob.glob("test_hdr_*.txt"):
        Path(f).unlink(missing_ok=True)
