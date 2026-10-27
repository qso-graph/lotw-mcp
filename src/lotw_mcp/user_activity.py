"""LoTW user activity checker — public CSV endpoint, cached locally."""

from __future__ import annotations

import csv
import io
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from . import __version__, _tls, ratelimit

_ACTIVITY_URL = "https://lotw.arrl.org/lotw-user-activity.csv"
_CACHE_TTL = 604800.0  # 7 days (file changes weekly)


def _cache_dir() -> Path:
    """Cache directory for user activity CSV."""
    d = Path.home() / ".cache" / "lotw-mcp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _is_mock() -> bool:
    return os.getenv("LOTW_MCP_MOCK") == "1"


_MOCK_CSV = """Callsign,Upload Date,Num QSO
W1AW,2026-03-01 12:00:00,45000
KI7MT,2026-02-28 18:30:00,1547
JA1ABC,2026-02-15 09:00:00,12000
"""

# In-memory index: callsign -> (last_upload, num_qso)
_index: dict[str, tuple[str, str]] | None = None
_index_time: float = 0.0


def _load_index() -> dict[str, tuple[str, str]]:
    """Load or refresh the user activity index."""
    global _index, _index_time

    now = time.time()
    if _index is not None and (now - _index_time) < _CACHE_TTL:
        return _index

    if _is_mock():
        text = _MOCK_CSV
    else:
        cache_file = _cache_dir() / "lotw-user-activity.csv"

        # Use cached file if fresh enough
        if cache_file.exists():
            age = now - cache_file.stat().st_mtime
            if age < _CACHE_TTL:
                text = cache_file.read_text(encoding="utf-8", errors="replace")
            else:
                text = _download(cache_file)
        else:
            text = _download(cache_file)

    idx: dict[str, tuple[str, str]] = {}
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) >= 2 and row[0] and row[0] != "Callsign":
            call = row[0].strip().upper()
            upload = row[1].strip() if len(row) > 1 else ""
            num = row[2].strip() if len(row) > 2 else ""
            idx[call] = (upload, num)

    _index = idx
    _index_time = now
    return idx


def _download(cache_file: Path) -> str:
    """Download the CSV and write to cache."""
    req = urllib.request.Request(_ACTIVITY_URL, method="GET")
    req.add_header("User-Agent", f"lotw-mcp/{__version__}")
    ratelimit.wait(_ACTIVITY_URL)
    try:
        with urllib.request.urlopen(req, timeout=120, context=_tls.context()) as resp:
            text: str = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # The activity list is a plain public file, but a 429 on it is still
        # LoTW telling this client to stop, and the block it arms is shared
        # with client.py -- the limit is LoTW's view of us, not of one URL.
        if exc.code == 429 or (exc.code == 503 and exc.headers.get("Retry-After")):
            raise ratelimit.RateLimited(
                ratelimit.block(_ACTIVITY_URL, exc.headers.get("Retry-After"))
            ) from None
        raise
    cache_file.write_text(text, encoding="utf-8")
    return text


def check_user(callsign: str) -> dict[str, Any]:
    """Check if a callsign uses LoTW and when they last uploaded."""
    call = callsign.strip().upper()
    idx = _load_index()
    entry = idx.get(call)

    if entry is None:
        return {
            "callsign": call,
            "uses_lotw": False,
            "last_upload": None,
        }

    upload, num = entry
    result: dict[str, Any] = {
        "callsign": call,
        "uses_lotw": True,
        "last_upload": upload,
    }
    if num:
        try:
            result["num_qso"] = int(num)
        except ValueError:
            pass

    return result
