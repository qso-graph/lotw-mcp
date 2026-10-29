"""Spacing between requests to ARRL Logbook of The World.

The ARRL publishes no request limit for LoTW's query endpoints. It is run for
the amateur community and its report queries are expensive on their side --
user_activity allows a 120 second timeout -- so this server spaces its requests
rather than sending them as fast as they are asked for.

This is not throttling the user (KI7MT, 2026-10-11): it limits what this server
sends to somebody else's service, and does not limit the person asking. The
cache in client.py, holding confirmations seven days does the larger share of
the work -- it removes requests rather than delaying them -- and this covers
what the cache cannot: a model calling tools in a loop over inputs that each
miss.
"""

from __future__ import annotations

import math
import threading
import time
import urllib.parse
from typing import Final

# Seconds between outbound requests.
# Matched to the fleet's default where a provider states nothing: sota-mcp and
# iota-mcp use the same 200 ms, iota's comment calling it "good neighbor". Not
# invented here, and not claimed to be the ARRL's published figure, because
# there is none.
MIN_INTERVAL: Final[float] = 0.2


# State is keyed by host, not shared across all of them.
#
# Spacing and a 429 are both one provider's business. This module is reached
# from calls to more than one host in some servers, and a global block there
# would mean a 429 from one service silencing a different, healthy one for up to
# an hour -- a working tool broken by an unrelated provider's limit. So a host
# gets its own gap and its own block.
_lock = threading.Lock()
_last: dict[str, float] = {}
_blocked_until: dict[str, float] = {}


class RateLimited(RuntimeError):
    """A provider asked us to stop. The message names which one, and is
    safe to show a user.

    A RuntimeError subclass so callers that already handle this client's
    failures keep working, and so FastMCP flags the tool result isError either
    way.
    """

    def __init__(self, wait_seconds: float, host: str = "") -> None:
        self.retry_after = max(1, round(wait_seconds))
        self.host = host
        who = host or "the service"
        super().__init__(
            f"{who} is rate limiting this client; try again in "
            f"{self.retry_after} s"
        )


def host_of(url: str) -> str:
    """The host a URL addresses, lower-cased, or "" if it has none.

    Used as the state key. A URL that cannot be parsed shares the ""
    bucket rather than escaping the limits, because the failure mode to avoid
    is sending the request, not mis-labelling it.
    """
    try:
        return urllib.parse.urlsplit(url).hostname or ""
    except ValueError:
        return ""


def wait(url: str) -> None:
    """Block until MIN_INTERVAL has passed since the previous request to this host.

    Raises RateLimited if this host has told us to stop and the interval it
    asked for has not passed. It does not sleep through that wait: an MCP server
    answers a synchronous tool call behind a client timeout, so waiting out an
    hour inside one is a hang rather than restraint. It refuses, and the message
    says when to come back.

    The spacing sleep is taken *outside* the lock, and the loop re-reads the
    state after it. Both matter. Holding the lock across a sleep would make one
    host's gap delay a request to a different host, which is the whole point of
    keying by host; and not re-reading would let a request go out that a 429
    arriving during the sleep had just forbidden.
    """
    host = host_of(url)
    while True:
        with _lock:
            now = time.monotonic()
            remaining = _blocked_until.get(host, 0.0) - now
            if remaining > 0:
                raise RateLimited(remaining, host)
            elapsed = now - _last.get(host, 0.0)
            if elapsed >= MIN_INTERVAL:
                _last[host] = now
                return
            delay = MIN_INTERVAL - elapsed
        time.sleep(delay)


# --- what to do when a provider says stop ---------------------------------
#
# A 429 carrying Retry-After is the provider stating its limit outright, and it
# is the most explicit form of the stated limit guarantee 8 requires honouring.
# The interval is bounded rather than taken verbatim: a header asking for a day
# would strand an interactive tool, and one asking for nothing would let us
# hammer. See qso-graph-devel/planning/MCP-SECURITY-FRAMEWORK.md.
MIN_BACKOFF: Final[float] = 60.0
MAX_BACKOFF: Final[float] = 3600.0


def retry_after(header: str | None) -> float:
    """Seconds to wait, from a Retry-After header, clamped to our bounds.

    Retry-After may also be an HTTP date. That form is not parsed and falls back
    to the floor rather than guessing, because a wrong parse would either hammer
    the provider or strand the user.
    """
    try:
        seconds = float(header) if header else 0.0
    except ValueError:
        seconds = 0.0
    # "nan" and "inf" parse as floats, and nan defeats the clamp below: every
    # comparison against it is False, so it would survive to be added to a
    # deadline that is then never in the future, leaving the block off
    # altogether. A header we cannot make sense of means the floor.
    if not math.isfinite(seconds):
        seconds = 0.0
    return min(max(seconds, MIN_BACKOFF), MAX_BACKOFF)


def block(url: str, header: str | None) -> float:
    """Honour a 429: stop sending to this host for the interval it asked for.

    Returns the wait that is actually in force, for the error the caller
    raises -- which is not always the interval just asked for. An outstanding
    block is never shortened: a response asking for 60 s that lands while a
    300 s block is still running must not release us at 60, and two concurrent
    responses would otherwise hand two callers different answers depending on
    which wrote last.

    The block covers every path on the host, because a limit is the provider's
    view of this client and not of one URL -- and only that host, because it is
    not a view of anybody else's service.
    """
    seconds = retry_after(header)
    host = host_of(url)
    with _lock:
        now = time.monotonic()
        standing = _blocked_until.get(host, 0.0)
        asked = now + seconds
        if asked >= standing:
            _blocked_until[host] = asked
            # `seconds`, not `asked - now`. The subtraction re-derives a number
            # we already hold and loses precision doing it: (now + 300.0) - now
            # is not 300.0 for about 4% of plausible time.monotonic() values,
            # and the worst regime is a freshly booted machine, where monotonic
            # is small -- which is every CI runner. It failed one job of the 39
            # in the 2026-10-29 patch release and blocked ionis-mcp 1.6.1.
            return seconds
        # An earlier, longer block is still in force. This is the one path that
        # must subtract, because the remaining wait is genuinely a difference,
        # and no caller is promised an exact figure for it.
        return standing - now


def clear() -> None:
    """Forget every gap and block. For tests, which share this module's state."""
    with _lock:
        _last.clear()
        _blocked_until.clear()
