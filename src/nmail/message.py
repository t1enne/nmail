"""Mail message parsing and rendering."""

from __future__ import annotations

import email
import email.policy
import html
import re
from pathlib import Path


def decode_rfc2047(s: str) -> str:
    """Decode RFC2047 encoded-word headers to plain text."""
    from email.header import decode_header

    parts = []
    for decoded, charset in decode_header(s):
        if isinstance(decoded, bytes):
            parts.append(decoded.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(decoded)
    return "".join(parts)


def render_mail(path: Path) -> str:
    """Render a mail file as readable markdown-style text.

    Returns headers in bold, a separator, then the decoded body.
    Returns empty string if file not found.
    """
    if not path.exists() or not path.is_file():
        return ""
    raw = path.read_text(errors="replace")
    msg = email.message_from_string(raw, policy=email.policy.compat32)

    lines: list[str] = []

    for hdr in ("From", "To", "Cc", "Subject", "Date"):
        val = msg.get(hdr)
        if val:
            lines.append(f"**{hdr}:** {decode_rfc2047(val)}")

    lines.append("")
    lines.append("---")
    lines.append("")

    body = _extract_body(msg)
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def _looks_like_html(text: str) -> bool:
    """Heuristic: does this text/plain body actually contain HTML or CSS?"""
    if re.search(r"<(?:html|head|style|script|body|div|br|p\b|a\s)", text, re.IGNORECASE):
        return True
    # CSS fragments like "a {text-decoration: none}" or "{font-family:...}"
    if re.search(r"[{]\s*(?:margin|padding|font-|text-|color|background|display|border|width|height|mso-)", text, re.IGNORECASE):
        return True
    return False


def _extract_body(msg) -> str:
    """Extract readable body, preferring text/plain over text/html."""
    if msg.is_multipart():
        parts = _walk_parts(msg)
        for ct, payload in parts:
            if ct == "text/plain" and not _looks_like_html(payload):
                return payload
        for ct, payload in parts:
            if ct == "text/html":
                return _strip_html(payload)
        # Fallback: first text/plain even if it looks like HTML — strip it
        for ct, payload in parts:
            if ct == "text/plain":
                return _strip_html(payload)
        if parts:
            return parts[0][1]
        return ""

    ct = msg.get_content_type()
    payload = _get_decoded_payload(msg)
    if ct == "text/html":
        return _strip_html(payload)
    if ct == "text/plain" and _looks_like_html(payload):
        return _strip_html(payload)
    return payload


def _walk_parts(msg) -> list[tuple[str, str]]:
    """Walk multipart message, returning (ct, decoded_payload) pairs."""
    parts: list[tuple[str, str]] = []
    for part in msg.walk():
        ct = part.get_content_type()
        if ct.startswith("multipart/"):
            continue
        payload = _get_decoded_payload(part)
        parts.append((ct, payload))
    return parts


def _get_decoded_payload(part) -> str:
    """Get decoded payload, handling base64, quoted-printable, etc."""
    ct = part.get_content_type()
    if ct not in ("text/plain", "text/html") and not ct.startswith("text/"):
        return ""
    charset = part.get_content_charset()
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    if isinstance(payload, bytes):
        try:
            return payload.decode(charset or "utf-8", errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")
    return str(payload)


def _strip_html(text: str) -> str:
    """Strip HTML tags to plain text."""
    text = html.unescape(text)
    # Remove <style> and <script> blocks entirely (contents are CSS/JS, not text)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Block-level → newlines
    text = re.sub(r"<(?:br|p|div|/p|/div)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "\n  • ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
    # Strip style attributes (handle tags with embedded > like <%...%> links)
    text = re.sub(r'\s*style\s*=\s*"[^"]*"', "", text, flags=re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = re.sub(r"^\s+", "", text, flags=re.MULTILINE)
    return text.strip()
