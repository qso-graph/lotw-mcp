"""MCP server for ARRL Logbook of The World — QSO query, QSL status, DXCC credit"""

from __future__ import annotations

try:
    from importlib.metadata import version

    __version__ = version("lotw-mcp")
except Exception:
    __version__ = "0.0.0-dev"
