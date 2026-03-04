"""ADIF response parser for LoTW API responses."""

from __future__ import annotations

import re

# ADIF field regex: <FIELD:LEN>VALUE or <FIELD:LEN:TYPE>VALUE
_ADIF_FIELD_RE = re.compile(r"<(\w+):(\d+)(?::\w+)?>", re.IGNORECASE)


def parse_adif(text: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Parse ADIF text into header fields and a list of record dicts.

    Returns:
        (header_fields, records) — header contains APP_LoTW_* metadata.
    """
    header: dict[str, str] = {}
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}

    upper = text.upper()
    eoh = upper.find("<EOH>")

    # Parse header fields
    if eoh >= 0:
        _parse_fields(text[:eoh], header)
        pos = eoh + 5
    else:
        pos = 0

    # Parse records
    while pos < len(text):
        if upper[pos:pos + 5] == "<EOR>":
            if current:
                records.append(current)
                current = {}
            pos += 5
            continue

        m = _ADIF_FIELD_RE.match(text, pos)
        if m:
            field = m.group(1).upper()
            length = int(m.group(2))
            value_start = m.end()
            value = text[value_start:value_start + length].strip()
            current[field] = value
            pos = value_start + length
        else:
            pos += 1

    if current:
        records.append(current)

    return header, records


def _parse_fields(text: str, out: dict[str, str]) -> None:
    """Extract ADIF fields from a chunk of text into out dict."""
    pos = 0
    while pos < len(text):
        m = _ADIF_FIELD_RE.match(text, pos)
        if m:
            field = m.group(1).upper()
            length = int(m.group(2))
            value_start = m.end()
            value = text[value_start:value_start + length].strip()
            out[field] = value
            pos = value_start + length
        else:
            pos += 1


def is_adif_response(text: str) -> bool:
    """Check if text looks like an ADIF response (has <EOH>)."""
    return "<EOH>" in text.upper() or "<eoh>" in text


def is_error_response(text: str) -> bool:
    """Check if text is an HTML error page (no <EOH>)."""
    return not is_adif_response(text) and "<html" in text.lower()
