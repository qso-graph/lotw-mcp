"""The server spaces its requests to ARRL Logbook of The World.

Asserting it because a convention nobody asserts drifts -- which is how
get_version_info drifted across this fleet.
"""

from __future__ import annotations

import time

from lotw_mcp import ratelimit


def test_min_interval_is_declared_and_positive():
    assert ratelimit.MIN_INTERVAL > 0


def test_consecutive_calls_are_spaced():
    ratelimit.wait()                      # establish the baseline
    start = time.monotonic()
    ratelimit.wait()
    elapsed = time.monotonic() - start
    # Allow a little slack for a slow scheduler, but it must actually wait.
    assert elapsed >= ratelimit.MIN_INTERVAL * 0.8, (
        f"second call returned after {elapsed:.3f}s, "
        f"MIN_INTERVAL is {ratelimit.MIN_INTERVAL}"
    )


def test_a_gap_longer_than_the_interval_is_not_padded():
    ratelimit.wait()
    time.sleep(ratelimit.MIN_INTERVAL * 1.2)
    start = time.monotonic()
    ratelimit.wait()
    # Nothing to wait for: the gap already passed.
    assert time.monotonic() - start < ratelimit.MIN_INTERVAL * 0.5
