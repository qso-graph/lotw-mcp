"""lotw-mcp: MCP server for ARRL Logbook of The World."""

from __future__ import annotations

import sys
from typing import Any

from fastmcp import FastMCP

from qso_graph_auth.identity import PersonaManager

from . import __version__
from .client import download_adif, query_confirmations, query_dxcc_credits, query_qsos
from .user_activity import check_user

mcp = FastMCP(
    "lotw-mcp",
    version=__version__,
    instructions=(
        "MCP server for ARRL Logbook of The World (LoTW) — "
        "query confirmations, QSOs, DXCC credits, and user activity"
    ),
)


def _pm() -> PersonaManager:
    return PersonaManager()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def lotw_confirmations(
    persona: str,
    since: str | None = None,
    band: str | None = None,
    mode: str | None = None,
    callsign: str | None = None,
    dxcc: int | None = None,
    detail: bool = True,
) -> dict[str, Any]:
    """Query confirmed QSL records from LoTW.

    Args:
        persona: Persona name configured in adif-mcp.
        since: QSLs received since this date (YYYY-MM-DD). Default: last 30 days.
        band: Filter by ADIF band (e.g., '20M').
        mode: Filter by ADIF mode (e.g., 'FT8').
        callsign: Filter by worked station callsign.
        dxcc: Filter by DXCC entity code.
        detail: Include QSL station location data (default true).

    Returns:
        Total count and list of confirmed QSO records.
    """
    try:
        return query_confirmations(_pm(), persona, since, band, mode, callsign, dxcc, detail)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def lotw_qsos(
    persona: str,
    since: str | None = None,
    band: str | None = None,
    mode: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Query all uploaded QSOs from LoTW (confirmed and unconfirmed).

    Args:
        persona: Persona name configured in adif-mcp.
        since: QSOs uploaded since this date (YYYY-MM-DD). Default: last 30 days.
        band: Filter by band (e.g., '20M').
        mode: Filter by mode (e.g., 'FT8').
        start_date: QSO date range start (YYYY-MM-DD).
        end_date: QSO date range end (YYYY-MM-DD).

    Returns:
        Total count and list of QSO records.
    """
    try:
        return query_qsos(_pm(), persona, since, band, mode, start_date, end_date)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def lotw_dxcc_credits(
    persona: str,
    entity: int | None = None,
) -> dict[str, Any]:
    """Query DXCC award credits from LoTW confirmations.

    Args:
        persona: Persona name configured in adif-mcp.
        entity: Optional DXCC entity code to filter by.

    Returns:
        Total credits and list of credited QSOs with award details.
    """
    try:
        return query_dxcc_credits(_pm(), persona, entity)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def lotw_download(
    persona: str,
    qsl_only: bool = False,
    since: str | None = None,
    band: str | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Download your complete LoTW log as raw ADIF text.

    Returns the .adi file content — save to disk for import into your logger.
    Set qsl_only=True for confirmed QSLs only. Omit 'since' for full history.
    Warning: large logs may take 30-60 seconds (LoTW is slow).

    Args:
        persona: Persona name configured in adif-mcp.
        qsl_only: Only return confirmed QSLs (default: all uploaded QSOs).
        since: Only records since this date (YYYY-MM-DD). Omit for full history.
        band: Filter by band (e.g., '20M').
        mode: Filter by mode (e.g., 'FT8').

    Returns:
        Raw ADIF text and record count.
    """
    try:
        return download_adif(_pm(), persona, qsl_only=qsl_only, since=since, band=band, mode=mode)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def lotw_user_activity(callsign: str) -> dict[str, Any]:
    """Check if a callsign uses LoTW and when they last uploaded.

    Public endpoint — no authentication required. Uses a locally cached
    copy of the LoTW user activity CSV (refreshed weekly).

    Args:
        callsign: Callsign to check.

    Returns:
        Whether the callsign uses LoTW and their last upload date.
    """
    try:
        return check_user(callsign)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the lotw-mcp server."""
    transport = "stdio"
    port = 8004
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--transport" and i < len(sys.argv) - 1:
            transport = sys.argv[i + 1]
        if arg == "--port" and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])

    if transport == "streamable-http":
        mcp.run(transport=transport, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
