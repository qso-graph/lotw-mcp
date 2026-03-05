"""LoTW HTTP client — wraps the ADIF query endpoints."""

from __future__ import annotations

import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from adif_mcp.credentials import get_creds

from .adif_parser import is_adif_response, is_error_response, parse_adif

_BASE = "https://lotw.arrl.org/lotwuser/lotwreport.adi"

# Mock ADIF for testing
_MOCK_CONFIRMATIONS = """ARRL Logbook of The World Status Report
<PROGRAMID:4>LoTW
<APP_LoTW_LASTQSL:19>2026-03-01 12:00:00
<APP_LoTW_NUMREC:1>2
<EOH>
<CALL:5>KI7MT<BAND:3>20M<MODE:3>FT8<QSO_DATE:8>20260301<TIME_ON:6>012345<QSL_RCVD:1>Y<QSLRDATE:8>20260302<DXCC:3>291<COUNTRY:13>United States<GRIDSQUARE:6>DN13sa<CQZ:1>3<ITUZ:2>10<CREDIT_GRANTED:23>DXCC:MIXED,DXCC:DIGITAL<EOR>
<CALL:4>W1AW<BAND:3>40M<MODE:2>CW<QSO_DATE:8>20260228<TIME_ON:6>200000<QSL_RCVD:1>Y<QSLRDATE:8>20260301<DXCC:3>291<COUNTRY:13>United States<GRIDSQUARE:6>FN31pr<CQZ:1>5<ITUZ:1>8<EOR>
"""

_MOCK_QSOS = """ARRL Logbook of The World Status Report
<PROGRAMID:4>LoTW
<APP_LoTW_LASTQSORX:19>2026-03-01 12:00:00
<APP_LoTW_NUMREC:1>3
<EOH>
<CALL:5>KI7MT<BAND:3>20M<MODE:3>FT8<QSO_DATE:8>20260301<TIME_ON:6>012345<QSL_RCVD:1>Y<EOR>
<CALL:4>W1AW<BAND:3>40M<MODE:2>CW<QSO_DATE:8>20260228<TIME_ON:6>200000<QSL_RCVD:1>Y<EOR>
<CALL:5>JA1AB<BAND:3>15M<MODE:3>FT8<QSO_DATE:8>20260227<TIME_ON:6>153000<QSL_RCVD:1>N<EOR>
"""

_MOCK_DXCC = """ARRL Logbook of The World Status Report
<PROGRAMID:4>LoTW
<APP_LoTW_NUMREC:1>2
<EOH>
<CALL:5>JA1AB<QSO_DATE:8>20250915<MODE:3>FT8<BAND:3>20M<DXCC:3>339<COUNTRY:5>JAPAN<CREDIT_GRANTED:10>DXCC:MIXED<APP_LOTW_CREDIT_GRANTED:10>DXCC:MIXED<EOR>
<CALL:5>G3ABC<QSO_DATE:8>20251001<MODE:2>CW<BAND:3>40M<DXCC:3>223<COUNTRY:7>ENGLAND<CREDIT_GRANTED:18>DXCC:MIXED,DXCC:CW<APP_LOTW_CREDIT_GRANTED:18>DXCC:MIXED,DXCC:CW<EOR>
"""


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
    req.add_header("User-Agent", "lotw-mcp/0.1.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
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


def query_confirmations(
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

    creds = get_creds(persona, "lotw")
    if creds is None or not creds.username or not creds.password:
        return {"error": f"No LoTW credentials for persona '{persona}'. Set up with: adif-mcp creds set --persona {persona} --provider lotw --username <call> --password <pass>"}

    params: dict[str, str] = {
        "login": creds.username,
        "password": creds.password,
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
        return {"error": _extract_error(text)}

    header, records = parse_adif(text)
    return {
        "total": len(records),
        "last_qsl": header.get("APP_LOTW_LASTQSL", ""),
        "records": [_record_to_dict(r) for r in records],
    }


def query_qsos(
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

    creds = get_creds(persona, "lotw")
    if creds is None or not creds.username or not creds.password:
        return {"error": f"No LoTW credentials for persona '{persona}'."}

    params: dict[str, str] = {
        "login": creds.username,
        "password": creds.password,
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
        return {"error": _extract_error(text)}

    header, records = parse_adif(text)
    return {
        "total": len(records),
        "last_qso_rx": header.get("APP_LOTW_LASTQSORX", ""),
        "records": [_record_to_dict(r) for r in records],
    }


def query_dxcc_credits(
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

    creds = get_creds(persona, "lotw")
    if creds is None or not creds.username or not creds.password:
        return {"error": f"No LoTW credentials for persona '{persona}'."}

    # DXCC credits use a different endpoint
    url = "https://lotw.arrl.org/lotwuser/lotwreport.adi"
    params: dict[str, str] = {
        "login": creds.username,
        "password": creds.password,
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
        return {"error": _extract_error(text)}

    _, records = parse_adif(text)

    # Filter to only records with CREDIT_GRANTED
    credits = [_record_to_dict(r) for r in records if "CREDIT_GRANTED" in r]
    return {
        "total": len(credits),
        "credits": credits,
    }
