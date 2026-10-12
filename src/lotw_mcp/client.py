"""LoTW HTTP client — wraps the ADIF query endpoints."""

from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from qso_graph_auth.identity import PersonaManager

from . import __version__, _tls
from ._mock_adif import _MOCK_CONFIRMATIONS, _MOCK_DXCC, _MOCK_QSOS
from .adif_parser import is_error_response, parse_adif

_BASE = "https://lotw.arrl.org/lotwuser/lotwreport.adi"

def _is_mock() -> bool:
    return os.getenv("LOTW_MCP_MOCK") == "1"


def _default_since() -> str:
    """Default 'since' date: 30 days ago."""
    dt = datetime.now(timezone.utc) - timedelta(days=30)
    return dt.strftime("%Y-%m-%d")


def _get(url: str, params: dict[str, str], timeout: float = 120.0) -> str:
    """HTTP GET, return response text.

    Catches all urllib exceptions to prevent credential-bearing URLs
    from leaking through error messages (LoTW puts passwords in query params).
    """
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"
    req = urllib.request.Request(full_url, method="GET")
    req.add_header("User-Agent", f"lotw-mcp/{__version__}")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_tls.context()) as resp:
            # Annotated: the response object is Any to mypy, so decoding
            # it is Any too, and this function promises a str.
            body: str = resp.read().decode("utf-8", errors="replace")
            return body
    except Exception:
        raise RuntimeError("LoTW request failed — check network and credentials")


def _record_to_dict(rec: dict[str, str]) -> dict[str, Any]:
    """Normalize an ADIF record to a clean dict."""
    out: dict[str, Any] = {}
    for key, value in rec.items():
        lower = key.lower()
        # Convert known numeric fields
        if lower in ("dxcc", "cqz", "ituz"):
            try:
                out[lower] = int(value)
            except ValueError:
                out[lower] = value
        else:
            out[lower] = value
    return out


def _safe_error(html: str, secret: str | None) -> str:
    """LoTW's own message, or a fixed one when it cannot be shown safely.

    ``_extract_error`` lifts text out of an HTML page this project does not
    control, and this server's requests carry the password in the query string.
    A page whose ``<title>`` echoes the request would therefore put the password
    into the message — measured, not assumed: given such a page the secret came
    straight through. Until #23 that landed in a payload; it is now the error
    text a client reads.

    So the extracted text is passed on only when it carries neither the secret
    nor anything URL-shaped, and is capped. It is deliberately *not* scrubbed
    and handed over: a page containing the password is a surprise worth
    reporting as one rather than editing quietly.
    """
    message = _extract_error(html)
    if secret and secret in message:
        return "LoTW returned an error page that echoed the request; not shown"
    if "://" in message:
        return "LoTW returned an error page containing a URL; not shown"
    return message[:200]


def _extract_error(html: str) -> str:
    """Try to extract a useful error message from LoTW HTML error page."""
    # Look for common patterns
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"<b>(.*?)</b>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return "LoTW returned an error page (no ADIF data)"


def download_adif(
    pm: PersonaManager,
    persona: str,
    qsl_only: bool = False,
    since: str | None = None,
    band: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Download LoTW log as raw ADIF text.

    Omit 'since' for full history (uses 1970-01-01).
    Set qsl_only=True for confirmed QSLs only.
    Returns dict with 'adif' (raw text) and 'record_count'.
    """
    if _is_mock():
        text = _MOCK_CONFIRMATIONS if qsl_only else _MOCK_QSOS
        record_count = text.upper().count("<EOR>")
        return {"adif": text, "record_count": record_count}

    username, password = pm.require(persona, "lotw")

    params: dict[str, str] = {
        "login": username,
        "password": password,
        "qso_query": "1",
        "qso_withown": "yes",
    }
    if qsl_only:
        params["qso_qsl"] = "yes"
        params["qso_qslsince"] = since or "1970-01-01"
        params["qso_qsldetail"] = "yes"
    else:
        params["qso_qsl"] = "no"
        params["qso_qsorxsince"] = since or "1970-01-01"
    if band:
        params["qso_band"] = band.upper()
    if mode:
        params["qso_mode"] = mode.upper()

    text = _get(_BASE, params)

    if is_error_response(text):
        # Built first and raised second, so the raise interpolates only a
        # value already checked safe to show. test_error_messages_safe
        # reads the raise expression, and it is right to: a credential
        # named inside one is worth stopping on.
        message = _safe_error(text, password)
        raise RuntimeError(f"LoTW: {message}")

    record_count = text.upper().count("<EOR>")
    return {"adif": text, "record_count": record_count}


def query_confirmations(
    pm: PersonaManager,
    persona: str,
    since: str | None = None,
    band: str | None = None,
    mode: str | None = None,
    callsign: str | None = None,
    dxcc: int | None = None,
    detail: bool = True,
) -> dict[str, Any]:
    """Query confirmed QSL records from LoTW."""
    if _is_mock():
        header, records = parse_adif(_MOCK_CONFIRMATIONS)
        results = [_record_to_dict(r) for r in records]
        if band:
            results = [r for r in results if r.get("band", "").upper() == band.upper()]
        if mode:
            results = [r for r in results if r.get("mode", "").upper() == mode.upper()]
        if callsign:
            results = [r for r in results if r.get("call", "").upper() == callsign.upper()]
        return {
            "total": len(results),
            "last_qsl": header.get("APP_LOTW_LASTQSL", ""),
            "records": results,
        }

    username, password = pm.require(persona, "lotw")

    params: dict[str, str] = {
        "login": username,
        "password": password,
        "qso_query": "1",
        "qso_qsl": "yes",
        "qso_qslsince": since or _default_since(),
        "qso_withown": "yes",
    }
    if detail:
        params["qso_qsldetail"] = "yes"
    if band:
        params["qso_band"] = band.upper()
    if mode:
        params["qso_mode"] = mode.upper()
    if callsign:
        params["qso_callsign"] = callsign.upper()
    if dxcc is not None:
        params["qso_dxcc"] = str(dxcc)

    text = _get(_BASE, params)

    if is_error_response(text):
        # Built first and raised second, so the raise interpolates only a
        # value already checked safe to show. test_error_messages_safe
        # reads the raise expression, and it is right to: a credential
        # named inside one is worth stopping on.
        message = _safe_error(text, password)
        raise RuntimeError(f"LoTW: {message}")

    header, records = parse_adif(text)
    return {
        "total": len(records),
        "last_qsl": header.get("APP_LOTW_LASTQSL", ""),
        "records": [_record_to_dict(r) for r in records],
    }


def query_qsos(
    pm: PersonaManager,
    persona: str,
    since: str | None = None,
    band: str | None = None,
    mode: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Query all uploaded QSOs (confirmed and unconfirmed)."""
    if _is_mock():
        header, records = parse_adif(_MOCK_QSOS)
        results = [_record_to_dict(r) for r in records]
        if band:
            results = [r for r in results if r.get("band", "").upper() == band.upper()]
        if mode:
            results = [r for r in results if r.get("mode", "").upper() == mode.upper()]
        return {
            "total": len(results),
            "last_qso_rx": header.get("APP_LOTW_LASTQSORX", ""),
            "records": results,
        }

    username, password = pm.require(persona, "lotw")

    params: dict[str, str] = {
        "login": username,
        "password": password,
        "qso_query": "1",
        "qso_qsl": "no",
        "qso_qsorxsince": since or _default_since(),
        "qso_withown": "yes",
    }
    if band:
        params["qso_band"] = band.upper()
    if mode:
        params["qso_mode"] = mode.upper()
    if start_date:
        params["qso_startdate"] = start_date.replace("-", "")
    if end_date:
        params["qso_enddate"] = end_date.replace("-", "")

    text = _get(_BASE, params)

    if is_error_response(text):
        # Built first and raised second, so the raise interpolates only a
        # value already checked safe to show. test_error_messages_safe
        # reads the raise expression, and it is right to: a credential
        # named inside one is worth stopping on.
        message = _safe_error(text, password)
        raise RuntimeError(f"LoTW: {message}")

    header, records = parse_adif(text)
    return {
        "total": len(records),
        "last_qso_rx": header.get("APP_LOTW_LASTQSORX", ""),
        "records": [_record_to_dict(r) for r in records],
    }


def query_dxcc_credits(
    pm: PersonaManager,
    persona: str,
    entity: int | None = None,
) -> dict[str, Any]:
    """Query DXCC award credits."""
    if _is_mock():
        _, records = parse_adif(_MOCK_DXCC)
        return {
            "total": len(records),
            "credits": [_record_to_dict(r) for r in records],
        }

    username, password = pm.require(persona, "lotw")

    # DXCC credits use a different endpoint
    url = "https://lotw.arrl.org/lotwuser/lotwreport.adi"
    params: dict[str, str] = {
        "login": username,
        "password": password,
        "qso_query": "1",
        "qso_qsl": "yes",
        "qso_qslsince": "1900-01-01",  # all time
        "qso_withown": "yes",
        "qso_qsldetail": "yes",
    }
    if entity is not None:
        params["qso_dxcc"] = str(entity)

    text = _get(url, params)

    if is_error_response(text):
        # Built first and raised second, so the raise interpolates only a
        # value already checked safe to show. test_error_messages_safe
        # reads the raise expression, and it is right to: a credential
        # named inside one is worth stopping on.
        message = _safe_error(text, password)
        raise RuntimeError(f"LoTW: {message}")

    _, records = parse_adif(text)

    # Filter to only records with CREDIT_GRANTED
    credits = [_record_to_dict(r) for r in records if "CREDIT_GRANTED" in r]
    return {
        "total": len(credits),
        "credits": credits,
    }
