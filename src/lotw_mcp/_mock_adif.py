"""Sample LoTW responses, as LoTW sends them.

Their own module for one reason: they contain ADIF records, and an ADIF record
is written on one line. Measured rather than assumed — this project's parser is
not line-based, and wrapping a record between fields parses identically — so the
exemption below is not "wrapping would break it". It is that a wrapped sample
stops resembling what LoTW actually sends, and these exist precisely to stand in
for that. The same ground as solar-mcp keeping NOAA's alert text intact: the
shape is the point.

Keeping them here rather than in client.py confines the exemption to a file
holding nothing but sample data. A `per-file-ignores` entry on client.py would
have exempted several hundred lines of real code from E501 for the sake of two
lines of ADIF.
"""

# ruff: noqa: E501

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
