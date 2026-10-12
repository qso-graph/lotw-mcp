"""Conformance with the Model Context Protocol, revision 2026-07-28.

Nothing in this project's documents required this until 2026-10-11 — not
CLAUDE.md, not .claude/rules/security.md, not MCP-SECURITY-FRAMEWORK.md, not
qso-graph-spec. We documented how to *publish* an MCP server in detail and
never wrote down what makes one *valid*, which is how a missing ``isError`` and
missing annotations reached all 22 servers in the fleet unnoticed.

So these are asserted rather than trusted.

Follows ``adif-mcp``, ``solar-mcp``, ``pota-mcp``, ``wspr-mcp``, ``iota-mcp``
and ``hamqth-mcp``. Like hamqth-mcp this server holds the operator's
credentials and the provider puts the password in query parameters — but the
hazard here is a different one and had to be measured rather than assumed.
``_extract_error`` lifts text out of an HTML page nobody here controls, so a
page echoing the request carries the password into the message. Until #23 that
landed in a payload; it is now the error text a client reads.
``TestNoFailurePathCarriesTheSecret`` drives exactly that page.

Test IDs: LOTW-C01 onward.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from fastmcp.exceptions import ToolError

os.environ["LOTW_MCP_MOCK"] = "1"

from lotw_mcp import server  # noqa: E402

ANNOTATION_HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

# Four send the operator's LoTW password; one reads a public activity CSV.
# Both reach lotw.arrl.org, so both are open-world; the split is recorded
# because it is what a reader most needs to know about this server.
NEEDS_CREDENTIALS = {"lotw_confirmations", "lotw_qsos", "lotw_dxcc_credits", "lotw_download"}
PUBLIC_ENDPOINTS = {"lotw_user_activity"}
READS_LOTW = NEEDS_CREDENTIALS | PUBLIC_ENDPOINTS
ANSWERS_FROM_THE_PACKAGE = {"get_version_info"}


def _tools() -> dict[str, object]:
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


def _wire(tool: object) -> dict[str, object]:
    """The serialised annotations, which is what a client reads."""
    annotations = getattr(tool, "annotations", None)
    assert annotations is not None, "tool declares no annotations"
    return annotations.model_dump(by_alias=True, exclude_none=True)


def _call(name: str):
    """The underlying function of a registered tool."""
    tool = getattr(server, name)
    return getattr(tool, "fn", tool)


class TestToolAnnotations:
    def test_every_tool_declares_all_four_hints(self) -> None:
        """LOTW-C01: the defaults are pessimistic, so silence is the wrong answer."""
        for name, tool in _tools().items():
            wire = _wire(tool)
            for hint in ANNOTATION_HINTS:
                assert hint in wire, f"{name} omits {hint} on the wire; got {sorted(wire)}"

    def test_every_tool_reads_and_none_writes(self) -> None:
        """LOTW-C02: the three hints that describe effect.

        Nothing here uploads to LoTW, and no credential is ever written — the
        keyring is read only. ``lotw_download`` writes nothing either: it
        returns the ADIF as text rather than saving a file.
        """
        for name, tool in _tools().items():
            wire = _wire(tool)
            assert wire["readOnlyHint"] is True, name
            assert wire["destructiveHint"] is False, name
            assert wire["idempotentHint"] is True, name

    def test_open_world_is_read_per_tool(self) -> None:
        """LOTW-C03: five reach lotw.arrl.org; one does not."""
        tools = _tools()
        assert set(tools) == READS_LOTW | ANSWERS_FROM_THE_PACKAGE
        for name in READS_LOTW:
            assert _wire(tools[name])["openWorldHint"] is True, name
        for name in ANSWERS_FROM_THE_PACKAGE:
            assert _wire(tools[name])["openWorldHint"] is False, name


class TestToolErrorsAreFlagged:
    """A tool execution error belongs in the result with ``isError: true``.

    The specification states the cost of getting this wrong: otherwise "the LLM
    would not be able to see that an error occurred and self-correct". These
    returned ``{"error": "..."}`` as a *successful* result until #23.
    """

    @pytest.fixture
    def broken(self, monkeypatch):
        """Every query failing the way an unreachable LoTW does."""
        def fail(*_args, **_kwargs):
            raise RuntimeError("LoTW request failed — check network and credentials")

        for name in ("query_confirmations", "query_qsos", "query_dxcc_credits",
                     "download_adif", "check_user"):
            monkeypatch.setattr(server, name, fail, raising=False)

    UPSTREAM_CASES = [
        ("lotw_confirmations", {"persona": "p"}),
        ("lotw_qsos", {"persona": "p"}),
        ("lotw_dxcc_credits", {"persona": "p"}),
        ("lotw_download", {"persona": "p"}),
        ("lotw_user_activity", {"callsign": "KI7MT"}),
    ]

    def test_the_cases_cover_every_tool_that_reaches_lotw(self) -> None:
        """LOTW-C09: the parametrisation below cannot silently miss one."""
        assert {name for name, _ in self.UPSTREAM_CASES} == READS_LOTW

    @pytest.mark.parametrize("name,kwargs", UPSTREAM_CASES)
    def test_an_upstream_failure_is_flagged(self, broken, name, kwargs) -> None:
        """LOTW-C10: every tool that can fail, not a sample of them."""
        with pytest.raises(ToolError, match="LoTW request failed"):
            _call(name)(**kwargs)

    def test_lotws_own_refusal_is_flagged_and_passed_on(self, monkeypatch) -> None:
        """LOTW-C11: "Login failed" is what a model should see.

        LoTW answers a bad login with an HTML page rather than a status code,
        which is why ``is_error_response`` exists. That verdict used to be
        returned as a successful result carrying an ``error`` key.
        """
        from lotw_mcp import client

        monkeypatch.delenv("LOTW_MCP_MOCK", raising=False)
        monkeypatch.setattr(
            client, "_get",
            lambda *a, **k: "<html><title>Login failed</title></html>",
        )
        monkeypatch.setattr(
            client.PersonaManager, "require",
            lambda self, persona, provider, prefer=None: ("KI7MT", "pw"),
            raising=False,
        )
        with pytest.raises(ToolError, match="Login failed"):
            _call("lotw_confirmations")(persona="p")


class TestNoFailurePathCarriesTheSecret:
    """The hazard particular to this server, measured rather than assumed.

    ``_extract_error`` returns whatever is in the page's ``<title>`` or first
    ``<b>``. Those pages are LoTW's, not ours, and this server's requests put
    the password in the query string — so a page echoing the request puts the
    password in the message. Before #23 it did exactly that: given such a page
    the sentinel came straight through.

    The fix is not to scrub the secret out and hand the rest over. A page
    containing the password is a surprise worth reporting as one, so the text
    is withheld with a reason.
    """

    SENTINEL = "s3nt1nel-not-a-real-password"

    def test_a_page_echoing_the_request_is_withheld(self) -> None:
        """LOTW-C20: the measured case."""
        from lotw_mcp.client import _safe_error

        page = (f"<html><title>Login failed for "
                f"https://lotw.arrl.org/?login=KI7MT&password={self.SENTINEL}</title></html>")
        message = _safe_error(page, self.SENTINEL)
        assert self.SENTINEL not in message
        assert "echoed the request" in message

    def test_a_page_carrying_any_url_is_withheld(self) -> None:
        """LOTW-C21: not only the exact secret.

        Matching on the secret alone would pass a page quoting the request with
        the password truncated, or a different account's. Anything URL-shaped
        out of a page we do not control is withheld.
        """
        from lotw_mcp.client import _safe_error

        message = _safe_error("<title>See https://lotw.arrl.org/help</title>", self.SENTINEL)
        assert "containing a URL" in message

    def test_an_ordinary_lotw_message_still_reaches_the_caller(self) -> None:
        """LOTW-C22: the control — this withholds some pages, not all of them.

        If it withheld everything it would be safe and useless, and a model
        would lose the one thing it can act on.
        """
        from lotw_mcp.client import _safe_error

        assert _safe_error("<title>Login failed</title>", self.SENTINEL) == "Login failed"
        assert _safe_error("<b>Invalid callsign</b>", self.SENTINEL) == "Invalid callsign"

    def test_the_raise_interpolates_a_checked_value(self) -> None:
        """LOTW-C23: and the raise itself names no credential.

        ``test_error_messages_safe`` in test_security.py reads the raise
        expression and is right to: a credential named inside one is worth
        stopping on. The message is built in a named step first, so the raise
        carries only a value already checked.
        """
        import pathlib

        import lotw_mcp.client as client_module

        source = pathlib.Path(client_module.__file__).read_text()
        for line in source.splitlines():
            if line.strip().startswith("raise RuntimeError"):
                assert "password" not in line, line.strip()


class TestVersionInfoShape:
    def test_it_matches_the_shape_the_fleet_returns(self) -> None:
        """LOTW-C30: the convention that drifted because nobody asserted it."""
        info = _call("get_version_info")()
        assert info["service_name"] == "lotw-mcp"
        assert info["service_version"]
        assert info["spec_version"]

    def test_the_user_agent_is_the_version_actually_running(self) -> None:
        """LOTW-C31: it said 0.1.0 while the package was 0.3.8.

        ARRL sees this string. A hard-coded version drifts the moment one is
        cut, and four releases had gone by.
        """
        import pathlib

        import lotw_mcp.client as client_module
        import lotw_mcp.user_activity as activity_module

        for module in (client_module, activity_module):
            source = pathlib.Path(module.__file__).read_text()
            assert 'f"lotw-mcp/{__version__}"' in source, module.__name__
            assert "lotw-mcp/0.1.0" not in source, module.__name__


class TestRegistration:
    def test_the_six_tools_a_client_sees(self) -> None:
        """LOTW-C40: calling a function directly is not proof a client can."""
        assert set(_tools()) == READS_LOTW | ANSWERS_FROM_THE_PACKAGE
