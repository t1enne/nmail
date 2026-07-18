"""Markdown draft → RFC5322 MIME message."""

from __future__ import annotations

import email.message
import email.policy
import re
import uuid
from pathlib import Path


class DraftParts:
    """Parsed draft: headers block (RFC5322-style lines), markdown body, attachment list."""

    def __init__(
        self,
        headers: str,
        body: str,
        attachments: str = "",
    ) -> None:
        self.headers = headers
        self.body = body
        self.attachments = attachments


def parse_draft(path: Path) -> DraftParts:
    text = path.read_text()
    parts = text.split("\n---\n", 1)
    if len(parts) == 1:
        return DraftParts(headers="", body=parts[0])
    headers_block = parts[0].strip()
    rest = parts[1].strip()

    # Check for second --- separator (attachment list)
    if "\n---\n" in rest:
        body, atts = rest.split("\n---\n", 1)
        return DraftParts(headers=headers_block, body=body.strip(), attachments=atts.strip())
    return DraftParts(headers=headers_block, body=rest)


def _parse_headers_block(headers_str: str) -> dict[str, str]:
    """Parse RFC5322-style headers (one per line, key: value) into a dict."""
    result: dict[str, str] = {}
    for line in headers_str.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def _generate_boundary() -> str:
    return f"==============={uuid.uuid4().hex[:16]}"


def _plain_text(markdown: str) -> str:
    """Strip bare markdown markers for text/plain fallback. Simple but effective."""
    # Remove heading markers
    text = re.sub(r"^#{1,6}\s+", "", markdown, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove links → just text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # Remove code fences
    text = re.sub(r"```[^\n]*\n", "", text)
    text = re.sub(r"```", "", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Blockquotes
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Unordered lists
    text = re.sub(r"^\s*[-*+]\s+", "  ", text, flags=re.MULTILINE)
    # Ordered lists
    text = re.sub(r"^\s*\d+\.\s+", "  ", text, flags=re.MULTILINE)
    return text.strip()


def _strip_signature(body: str) -> str:
    """Strip signature block (everything after '-- ' on its own line)."""
    m = re.search(r"^-- $", body, re.MULTILINE)
    if m:
        return body[: m.start()].strip()
    return body


def render_message(path: Path, fmt: str = "mime") -> str:
    """Render a draft file into an RFC5322 MIME message.

    Args:
        path: Path to the markdown draft file.
        fmt: 'plain' for text/plain only, 'mime' for multipart/alternative,
             'html' for text/html only.
    """
    draft = parse_draft(path)
    headers_dict = _parse_headers_block(draft.headers)

    msg = email.message.EmailMessage()
    msg.policy = email.policy.default

    # Transfer known headers
    for hdr in (
        "From",
        "To",
        "Cc",
        "Bcc",
        "Subject",
        "Date",
        "Message-ID",
        "In-Reply-To",
        "References",
        "Reply-To",
    ):
        if hdr.lower() in (k.lower() for k in headers_dict):
            # Find matching key preserving original case
            for k, v in headers_dict.items():
                if k.lower() == hdr.lower() and v:
                    msg[k] = v

    # Date
    if "Date" not in msg:
        from email.utils import formatdate

        msg["Date"] = formatdate(localtime=True)

    # Message-ID
    if "Message-ID" not in msg:
        from email.utils import make_msgid

        msg["Message-ID"] = make_msgid()

    # MIME-Version
    msg["MIME-Version"] = "1.0"

    # User-Agent
    msg["User-Agent"] = "nmail"

    body = draft.body
    if fmt == "plain":
        msg.set_content(_plain_text(body))
    elif fmt == "html":
        msg.set_content(_plain_text(body))  # no markdown→html in core
    else:  # mime — multipart/alternative
        boundary = _generate_boundary()
        msg["Content-Type"] = f'multipart/alternative; boundary="{boundary}"'
        text_part = email.message.EmailMessage()
        text_part.set_content(_plain_text(body), subtype="plain", charset="utf-8")
        html_part = email.message.EmailMessage()
        html_part.set_content(
            f"<html><body><pre>{_plain_text(body)}</pre></body></html>",
            subtype="html",
            charset="utf-8",
        )
        msg.attach(text_part)
        msg.attach(html_part)

    return msg.as_string()
