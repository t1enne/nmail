"""Markdown draft → RFC5322 MIME message."""

from __future__ import annotations

import email.message
import email.policy
import html
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


def _markdown_to_html(md: str) -> str:
    """Convert markdown to HTML. No deps — regex-based, covers nmail's subset."""
    text = md

    # ── Block-level transforms (process line-by-line) ──
    lines = text.split("\n")
    out: list[str] = []
    in_blockquote = False
    in_code = False
    code_buf: list[str] = []
    code_lang = ""
    ul_buf: list[str] = []
    ol_buf: list[str] = []
    table_buf: list[str] = []

    def _flush_code() -> None:
        nonlocal in_code, code_buf, code_lang
        if code_buf:
            code = html.escape("\n".join(code_buf))
            cls = f' class="language-{html.escape(code_lang, quote=True)}"' if code_lang else ""
            out.append(f"<pre><code{cls}>{code}</code></pre>")
            code_buf = []
            code_lang = ""
            in_code = False

    def _flush_ul() -> None:
        nonlocal ul_buf
        if ul_buf:
            for item in ul_buf:
                out.append(f"<li>{_inline(item)}</li>")
            out[-len(ul_buf)] = f"<ul>{out[-len(ul_buf)]}"
            out.append("</ul>")
            ul_buf = []

    def _flush_ol() -> None:
        nonlocal ol_buf
        if ol_buf:
            for item in ol_buf:
                out.append(f"<li>{_inline(item)}</li>")
            out[-len(ol_buf)] = f"<ol>{out[-len(ol_buf)]}"
            out.append("</ol>")
            ol_buf = []

    def _flush_table() -> None:
        nonlocal table_buf
        if not table_buf:
            return
        # First row is header, second row is separator (already filtered)
        rows = []
        for i, row in enumerate(table_buf):
            cells = row.split("|")
            # Remove empty first/last from leading/trailing pipe
            if cells and not cells[0].strip():
                cells = cells[1:]
            if cells and not cells[-1].strip():
                cells = cells[:-1]
            cells = [c.strip() for c in cells]
            tag = "th" if i == 0 else "td"
            row_cells = "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells)
            rows.append(f"<tr>{row_cells}</tr>")
        table_html = "".join(rows)
        out.append(f"<table>{table_html}</table>")
        table_buf = []

    def _close_blockquote() -> None:
        nonlocal in_blockquote
        if in_blockquote:
            out.append("</blockquote>")
            in_blockquote = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code fence start/end
        if line.startswith("```"):
            if not in_code:
                _flush_ul()
                _flush_ol()
                _close_blockquote()
                in_code = True
                code_buf = []
                code_lang = line[3:].strip()
            else:
                _flush_code()
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Blank line — flush pending blocks
        if not line.strip():
            _flush_table()
            _flush_ul()
            _flush_ol()
            _close_blockquote()
            out.append("")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            _flush_table()
            _flush_ul()
            _flush_ol()
            _close_blockquote()
            out.append("<hr>")
            i += 1
            continue

        # Table row
        if line.startswith("|") and "|" in line[1:]:
            _flush_ul()
            _flush_ol()
            _close_blockquote()
            # Skip separator row (|---|...|)
            stripped = line.replace("|", "")
            if not (stripped and all(c in " -:" for c in stripped)):
                table_buf.append(line)
            i += 1
            continue
        else:
            _flush_table()

        # Headings
        hm = re.match(r"^(#{1,6})\s+(.+)$", line)
        if hm:
            _flush_ul()
            _flush_ol()
            _close_blockquote()
            level = len(hm.group(1))
            out.append(f"<h{level}>{_inline(hm.group(2))}</h{level}>")
            i += 1
            continue

        # Blockquotes
        qm = re.match(r"^>\s?(.*)$", line)
        if qm:
            _flush_ul()
            _flush_ol()
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            content = qm.group(1)
            out.append(_inline(content) if content else "")
            i += 1
            continue
        else:
            _close_blockquote()

        # Unordered list item
        um = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if um:
            _flush_table()
            _flush_ol()
            _close_blockquote()
            ul_buf.append(um.group(1))
            i += 1
            continue
        else:
            _flush_ul()

        # Ordered list item
        om = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if om:
            _flush_table()
            _flush_ul()
            _close_blockquote()
            ol_buf.append(om.group(1))
            i += 1
            continue
        else:
            _flush_ol()

        # Regular paragraph line — gather until blank, list, heading, hr, blockquote, or table
        _flush_table()
        _flush_ul()
        _flush_ol()
        para: list[str] = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if not nxt.strip() or nxt.startswith("|") or re.match(r"^[#>\-*_~]|\d+\.\s", nxt):
                break
            para.append(nxt)
            i += 1
        out.append(f"<p>{_inline(' '.join(p.strip() for p in para if p.strip()))}</p>")

    # Flush any remaining
    _flush_code()
    _flush_table()
    _flush_ul()
    _flush_ol()
    _close_blockquote()

    return "\n".join(out).strip()


def _inline(text: str) -> str:
    """Apply inline markdown transforms to a text string.

    First escapes HTML special chars (<, >, &) — markdown delimiters
    like ** * ` ~~ [ ] ( ) do not contain these so they survive.
    Then applies markdown-to-HTML regex substitutions.
    """
    text = html.escape(text, quote=False)
    # Bold italic *** or ___ — must run before bold/italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"___(.+?)___", r"<strong><em>\1</em></strong>", text)
    # Bold ** or __
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic * or _
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    # Strikethrough ~~
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Images before links
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


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
        msg.set_content(_markdown_to_html(body), subtype="html", charset="utf-8")
    else:  # mime — multipart/alternative
        boundary = _generate_boundary()
        msg["Content-Type"] = f'multipart/alternative; boundary="{boundary}"'
        text_part = email.message.EmailMessage()
        text_part.set_content(_plain_text(body), subtype="plain", charset="utf-8")
        html_part = email.message.EmailMessage()
        html_part.set_content(
            f"<html><body>{_markdown_to_html(body)}</body></html>",
            subtype="html",
            charset="utf-8",
        )
        msg.attach(text_part)
        msg.attach(html_part)

    return msg.as_string()
