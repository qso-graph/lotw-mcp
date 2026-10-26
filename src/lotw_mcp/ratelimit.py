"""Spacing between requests to ARRL Logbook of The World.

The ARRL publishes no request limit for LoTW's query endpoints. It is run for
the amateur community and its report queries are expensive on their side --
user_activity allows a 120 second timeout -- so this server spaces its requests
rather than sending them as fast as they are asked for.

This is not throttling the user (KI7MT, 2026-10-11): it limits what this server
sends to somebody else's service, and does not limit the person asking. The
cache in client.py, holding confirmations seven days does the larger share of the
work -- it removes requests rather than delaying them -- and this covers what the
cache cannot: a model calling tools in a loop over inputs that each miss.
"""

from __future__ import annotations

import threading
import time
from typing import Final

# Seconds between outbound requests.
# Matched to the fleet's default where a provider states nothing: sota-mcp and
# iota-mcp use the same 200 ms, iota's comment calling it "good neighbor". Not
# invented here, and not claimed to be the ARRL's published figure, because
# there is none.
MIN_INTERVAL: Final[float] = 0.2

_lock = threading.Lock()
_last: float = 0.0


def wait() -> None:
    """Block until MIN_INTERVAL has passed since the previous request.

    Held across threads by one lock, so concurrent tool calls queue rather than
    each measuring their own gap and all firing at once.
    """
    global _last
    with _lock:
        elapsed = time.monotonic() - _last
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        _last = time.monotonic()
