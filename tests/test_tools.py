"""L2 unit tests for lotw-mcp — all 5 tools + user activity helpers.

Uses LOTW_MCP_MOCK=1 for tool-level tests (no LoTW API calls).
Direct unit tests on filtering, date handling, and CSV parsing.

Test IDs: LOTW-L2-001 through LOTW-L2-045
"""

from __future__ import annotations

import os

import pytest

os.environ["LOTW_MCP_MOCK"] = "1"

from lotw_mcp.server import (
    lotw_confirmations,
    lotw_download,
    lotw_dxcc_credits,
    lotw_qsos,
    lotw_user_activity,
)
from lotw_mcp.user_activity import _load_index, check_user


# ---------------------------------------------------------------------------
# LOTW-L2-001..008: lotw_confirmations
# ---------------------------------------------------------------------------


class TestLotwConfirmations:
    def test_returns_records(self):
        """LOTW-L2-001: Confirmations returns 2 mock records."""
        result = lotw_confirmations(persona="test")
        assert result["total"] == 2
        assert len(result["records"]) == 2

    def test_band_filter(self):
        """LOTW-L2-002: Band filter returns matching records."""
        result = lotw_confirmations(persona="test", band="20M")
        assert result["total"] == 1
        assert result["records"][0]["call"] == "KI7MT"

    def test_mode_filter(self):
        """LOTW-L2-003: Mode filter returns matching records."""
        result = lotw_confirmations(persona="test", mode="CW")
        assert result["total"] == 1
        assert result["records"][0]["call"] == "W1AW"

    def test_record_fields(self):
        """LOTW-L2-004: Records have expected fields."""
        result = lotw_confirmations(persona="test")
        rec = result["records"][0]
        for field in ("call", "band", "mode", "qso_date"):
            assert field in rec, f"Missing field: {field}"

    def test_last_qsl_present(self):
        """LOTW-L2-005: Result includes last_qsl timestamp."""
        result = lotw_confirmations(persona="test")
        assert "last_qsl" in result


# ---------------------------------------------------------------------------
# LOTW-L2-010..017: lotw_download
# ---------------------------------------------------------------------------


class TestLotwDownload:
    def test_returns_raw_adif(self):
        """LOTW-L2-010: Download returns raw ADIF text."""
        result = lotw_download(persona="test")
        assert "adif" in result
        assert "<EOR>" in result["adif"].upper()

    def test_record_count_all(self):
        """LOTW-L2-011: qsl_only=False returns all records."""
        result = lotw_download(persona="test", qsl_only=False)
        assert result["record_count"] == 3

    def test_record_count_qsl_only(self):
        """LOTW-L2-012: qsl_only=True returns confirmed only."""
        result = lotw_download(persona="test", qsl_only=True)
        assert result["record_count"] == 2

    def test_full_history(self):
        """LOTW-L2-013: since=None downloads full history."""
        result = lotw_download(persona="test", since=None)
        assert result["record_count"] >= 2

    def test_adif_contains_callsigns(self):
        """LOTW-L2-014: ADIF text contains expected callsigns."""
        result = lotw_download(persona="test")
        assert "KI7MT" in result["adif"]
        assert "W1AW" in result["adif"]


# ---------------------------------------------------------------------------
# LOTW-L2-020..025: lotw_qsos
# ---------------------------------------------------------------------------


class TestLotwQsos:
    def test_returns_records(self):
        """LOTW-L2-020: QSOs returns 3 mock records."""
        result = lotw_qsos(persona="test")
        assert result["total"] == 3
        assert len(result["records"]) == 3

    def test_band_filter(self):
        """LOTW-L2-021: Band filter returns matching records."""
        result = lotw_qsos(persona="test", band="15M")
        assert result["total"] == 1
        assert result["records"][0]["call"] == "JA1AB"

    def test_mode_filter(self):
        """LOTW-L2-022: Mode filter returns matching records."""
        result = lotw_qsos(persona="test", mode="FT8")
        assert result["total"] >= 1

    def test_band_and_mode(self):
        """LOTW-L2-023: Combined band+mode filter."""
        result = lotw_qsos(persona="test", band="40M", mode="CW")
        assert result["total"] >= 1
        for rec in result["records"]:
            assert rec["band"] == "40M"
            assert rec["mode"] == "CW"

    def test_last_qso_rx_present(self):
        """LOTW-L2-024: Result includes last_qso_rx timestamp."""
        result = lotw_qsos(persona="test")
        assert "last_qso_rx" in result

    def test_record_fields(self):
        """LOTW-L2-025: QSO records have expected fields."""
        result = lotw_qsos(persona="test")
        rec = result["records"][0]
        for field in ("call", "band", "mode"):
            assert field in rec, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# LOTW-L2-026..028: lotw_dxcc_credits
# ---------------------------------------------------------------------------


class TestLotwDxccCredits:
    def test_returns_credits(self):
        """LOTW-L2-026: DXCC credits returns mock data."""
        result = lotw_dxcc_credits(persona="test")
        assert result["total"] == 2
        assert len(result["credits"]) == 2

    def test_credit_fields(self):
        """LOTW-L2-027: Credits have expected fields."""
        result = lotw_dxcc_credits(persona="test")
        credit = result["credits"][0]
        assert "call" in credit
        assert "dxcc" in credit or "country" in credit

    def test_credit_countries(self):
        """LOTW-L2-028: Mock credits include Japan and England."""
        result = lotw_dxcc_credits(persona="test")
        calls = [c["call"] for c in result["credits"]]
        assert "JA1AB" in calls
        assert "G3ABC" in calls


# ---------------------------------------------------------------------------
# LOTW-L2-030..037: lotw_user_activity + check_user
# ---------------------------------------------------------------------------


class TestLotwUserActivity:
    def test_known_user(self):
        """LOTW-L2-030: Known user returns uses_lotw=True."""
        result = lotw_user_activity(callsign="KI7MT")
        assert result["uses_lotw"] is True
        assert result["last_upload"] is not None

    def test_unknown_user(self):
        """LOTW-L2-031: Unknown user returns uses_lotw=False."""
        result = lotw_user_activity(callsign="ZZZZZ")
        assert result["uses_lotw"] is False

    def test_case_insensitive(self):
        """LOTW-L2-032: Callsign lookup is case-insensitive."""
        result = lotw_user_activity(callsign="ki7mt")
        assert result["uses_lotw"] is True

    def test_callsign_uppercased(self):
        """LOTW-L2-033: Result callsign is uppercase."""
        result = lotw_user_activity(callsign="ki7mt")
        assert result["callsign"] == "KI7MT"


class TestCheckUser:
    def test_direct_check(self):
        """LOTW-L2-034: check_user returns dict with uses_lotw."""
        result = check_user("W1AW")
        assert result["callsign"] == "W1AW"
        assert result["uses_lotw"] is True

    def test_num_qso_present(self):
        """LOTW-L2-035: Known user has num_qso field."""
        result = check_user("W1AW")
        assert "num_qso" in result
        assert result["num_qso"] == 45000

    def test_unknown_callsign(self):
        """LOTW-L2-036: Unknown callsign returns uses_lotw=False."""
        result = check_user("NOTREAL")
        assert result["uses_lotw"] is False
        assert result["last_upload"] is None

    def test_whitespace_stripped(self):
        """LOTW-L2-037: Whitespace in callsign stripped."""
        result = check_user("  KI7MT  ")
        assert result["callsign"] == "KI7MT"
        assert result["uses_lotw"] is True


# ---------------------------------------------------------------------------
# LOTW-L2-038..042: _load_index (CSV parsing)
# ---------------------------------------------------------------------------


class TestLoadIndex:
    def test_index_loaded(self):
        """LOTW-L2-038: Mock CSV index loads 3 entries."""
        idx = _load_index()
        assert len(idx) == 3

    def test_index_keys(self):
        """LOTW-L2-039: Index has expected callsigns."""
        idx = _load_index()
        assert "W1AW" in idx
        assert "KI7MT" in idx
        assert "JA1ABC" in idx

    def test_index_values(self):
        """LOTW-L2-040: Index values have (upload, num_qso) tuples."""
        idx = _load_index()
        upload, num = idx["KI7MT"]
        assert "2026-02-28" in upload
        assert num == "1547"

    def test_header_skipped(self):
        """LOTW-L2-041: CSV header row not in index."""
        idx = _load_index()
        assert "Callsign" not in idx

    def test_index_cached(self):
        """LOTW-L2-042: Second load returns same index."""
        idx1 = _load_index()
        idx2 = _load_index()
        assert idx1 is idx2
