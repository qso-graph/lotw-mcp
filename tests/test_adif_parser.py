"""LoTW's ADIF responses, read by qso_graph_lib.adif."""

from __future__ import annotations

from lotw_mcp.adif_parser import parse_adif

RESPONSE = """ARRL Logbook of the World Status Report
<PROGRAMID:4>LoTW
<APP_LoTW_LASTQSL:19>2026-10-28 12:00:00
<eoh>
<CALL:5>K1ABC<BAND:3>20M<QSL_RCVD:1>Y<eor>
<CALL:5>W9XYZ<BAND:3>40M<QSL_RCVD:1>Y<eor>
"""


def test_header_and_records_as_this_server_returns_them():
    header, records = parse_adif(RESPONSE)
    assert header == {"PROGRAMID": "LoTW", "APP_LOTW_LASTQSL": "2026-10-28 12:00:00"}
    assert [r["CALL"] for r in records] == ["K1ABC", "W9XYZ"]


def test_a_length_past_the_next_tag_does_not_run_two_qsos_together():
    """The old scanner read 'K1ABC<eor' and gave one QSO where there are two."""
    _, records = parse_adif("<eoh><CALL:9>K1ABC<eor><CALL:5>W9XYZ<eor>")
    assert [r["CALL"] for r in records] == ["K1ABC", "W9XYZ"]


def test_a_value_containing_a_tag_stays_one_field():
    _, records = parse_adif("<eoh><CALL:5>K1ABC<COMMENT:13>see <BAND:3>X<eor>")
    assert records == [{"CALL": "K1ABC", "COMMENT": "see <BAND:3>X"}]
