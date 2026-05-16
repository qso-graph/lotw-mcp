"""lotw-mcp: MCP server for ARRL Logbook of The World."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Final

try:
    _pkg_version = version("lotw-mcp")
except PackageNotFoundError:  # local dev / editable installs without dist metadata
    _pkg_version = "0.0.0-dev"

__version__: Final[str] = _pkg_version

# Upstream data spec the server is bound to. Pinned to the ARRL LoTW
# ADIF/CSV export schema revision we consume — bump this when ARRL
# changes the LoTW download format. Reported by the get_version_info
# tool so agents can detect fleet drift without going outside the
# MCP protocol.
__spec_version__: Final[str] = "lotw-arrl-v1"
