"""Tool tests for lotw-mcp — all 5 tools in mock mode."""

from __future__ import annotations

import os

os.environ["LOTW_MCP_MOCK"] = "1"

from lotw_mcp.server import (
    lotw_confirmations,
    lotw_download,
    lotw_dxcc_credits,
    lotw_qsos,
    lotw_user_activity,
)


# ---------------------------------------------------------------------------
# lotw_confirmations
# ---------------------------------------------------------------------------


class TestLotwConfirmations:
    def test_returns_records(self):
        result = lotw_confirmations(persona="test")
        assert result["total"] == 2
        assert len(result["records"]) == 2

    def test_band_filter(self):
        result = lotw_confirmations(persona="test", band="20M")
        assert result["total"] == 1
        assert result["records"][0]["call"] == "KI7MT"

    def test_mode_filter(self):
        result = lotw_confirmations(persona="test", mode="CW")
        assert result["total"] == 1
        assert result["records"][0]["call"] == "W1AW"


# ---------------------------------------------------------------------------
# lotw_download
# ---------------------------------------------------------------------------


class TestLotwDownload:
    def test_returns_raw_adif(self):
        result = lotw_download(persona="test")
        assert "adif" in result
        assert "<EOR>" in result["adif"].upper()

    def test_record_count_all(self):
        result = lotw_download(persona="test", qsl_only=False)
        assert result["record_count"] == 3

    def test_record_count_qsl_only(self):
        result = lotw_download(persona="test", qsl_only=True)
        assert result["record_count"] == 2

    def test_full_history(self):
        result = lotw_download(persona="test", since=None)
        assert result["record_count"] >= 2

    def test_adif_contains_callsigns(self):
        result = lotw_download(persona="test")
        assert "KI7MT" in result["adif"]
        assert "W1AW" in result["adif"]


# ---------------------------------------------------------------------------
# lotw_qsos
# ---------------------------------------------------------------------------


class TestLotwQsos:
    def test_returns_records(self):
        result = lotw_qsos(persona="test")
        assert result["total"] == 3
        assert len(result["records"]) == 3

    def test_band_filter(self):
        result = lotw_qsos(persona="test", band="15M")
        assert result["total"] == 1
        assert result["records"][0]["call"] == "JA1AB"


# ---------------------------------------------------------------------------
# lotw_dxcc_credits
# ---------------------------------------------------------------------------


class TestLotwDxccCredits:
    def test_returns_credits(self):
        result = lotw_dxcc_credits(persona="test")
        assert result["total"] == 2
        assert len(result["credits"]) == 2


# ---------------------------------------------------------------------------
# lotw_user_activity
# ---------------------------------------------------------------------------


class TestLotwUserActivity:
    def test_known_user(self):
        result = lotw_user_activity(callsign="KI7MT")
        assert result["uses_lotw"] is True
        assert result["last_upload"] is not None

    def test_unknown_user(self):
        result = lotw_user_activity(callsign="ZZZZZ")
        assert result["uses_lotw"] is False
