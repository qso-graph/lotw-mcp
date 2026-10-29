"""ADIF response parsing for LoTW API responses, on qso_graph_lib.adif.

The ADI itself is read by qso_graph_lib.adif, the fleet's one reader, as ADIF 3.1.7
defines it (and passing ADIF's own test files). This module had its own scanner,
which took exactly the declared length, so a length that ran past the next tag
swallowed it, ``<EOR>`` included, and ran two QSOs together.
"""

from __future__ import annotations

from qso_graph_lib import adif


def parse_adif(text: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Parse ADIF text into header fields and a list of record dicts.

    Names are upper-cased and values stripped, as this server has always returned them.

    Returns:
        (header_fields, records) — header contains APP_LoTW_* metadata.
    """
    doc = adif.read(text)
    header = {k: v.strip() for k, v in doc.header.items()}
    records = [{k: v.strip() for k, v in r.fields.items()} for r in doc.records]
    return header, records


def is_adif_response(text: str) -> bool:
    """Check if text looks like an ADIF response (has <EOH>)."""
    return "<EOH>" in text.upper() or "<eoh>" in text


def is_error_response(text: str) -> bool:
    """Check if text is an HTML error page (no <EOH>)."""
    return not is_adif_response(text) and "<html" in text.lower()
