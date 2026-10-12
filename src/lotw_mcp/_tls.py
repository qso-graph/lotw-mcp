"""The verifying TLS context this server's outbound calls use.

Its own module because the calls live in two files — ``client.py`` and
``user_activity.py`` — and a context defined in one and imported by the other
couples them for no reason. One job, imported by both, so
``test_every_outbound_call_verifies`` has one thing to point at.
"""

from __future__ import annotations

import ssl
from functools import cache

import certifi


@cache
def context() -> ssl.SSLContext:
    """A verifying context with a current root set. Built once.

    The roots come from ``certifi`` rather than whichever store the running
    Python was built against. On macOS that distinction is real: Apple ships
    ``/etc/ssl/cert.pem`` for OpenSSL — and therefore for Python — as a
    deliberately *reduced* file, 128 roots against the system keychain's 158.
    It is current, not stale. But a certificate chaining to one of the 30 it
    omits fails for Python while ``curl`` to the same URL succeeds
    (qso-graph-devel#73, found when meteor-mcp could not reach NASA at all).

    lotw.arrl.org verifies fine against the reduced file today, so this is a
    latent defect rather than an outage. It matters more here than in most of
    the fleet: **the operator's LoTW password travels over these connections**,
    in query parameters, because that is how LoTW's query interface works.

    Which is why verification is never disabled rather than merely why it
    should not be. ``ssl.CERT_NONE`` or ``check_hostname = False`` would make a
    failing call "work" by accepting any certificate from anyone, and on this
    server that means handing the password to whoever presented it. The fix is
    a complete root set, not a relaxed check.
    """
    return ssl.create_default_context(cafile=certifi.where())
