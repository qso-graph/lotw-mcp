# Changelog

All notable changes to `lotw-mcp` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- **Tool execution errors are flagged `isError`** (#23). Every tool returned `{"error": "..."}` on
  failure, which reaches a client as a *successful* call whose payload happens to contain the word
  "error". They now raise `ToolError`, which `fastmcp` reports as `isError: true`. **No decision
  changed — only how it is reported.** LoTW answers a bad login with an HTML page rather than a
  status code, and that verdict is still passed on: `Login failed` is what a model should see.
- **Fixed: LoTW's own error page could carry the password into the message.** `_extract_error`
  returns whatever is in the page's `<title>` or first `<b>`, and this server's requests put the
  password in the query string — so a page echoing the request put the password in the message.
  **Measured, not assumed:** given such a page the secret came straight through. Until now that
  landed in a payload; since #23 it is the error text a client reads. The extracted text is now
  withheld, with a reason, when it carries the secret or anything URL-shaped, and capped at 200
  characters. It is deliberately *not* scrubbed and handed over: a page containing the password is
  a surprise worth reporting as one rather than editing quietly. An ordinary `Login failed` still
  reaches the caller, which is the point.
- The four raises build their message in a named step first, so the `raise` interpolates only a
  value already checked. `test_error_messages_safe` reads the raise expression and is right to —
  a credential named inside one is worth stopping on.
- **Every tool declares all four annotation hints** (#23). All six are read-only, non-destructive
  and idempotent — nothing is uploaded to LoTW and no credential is ever written, only read.
  `openWorldHint` is true for the five that reach lotw.arrl.org (four sending the operator's
  password, one reading the public activity CSV) and false for `get_version_info`.
- **Fixed: the `User-Agent` said `lotw-mcp/0.1.0`** in both `client.py` and `user_activity.py`
  while the package was 0.3.8 — four releases of drift, visible to ARRL. It now reports
  `__version__`.
- **`tests/test_mcp_conformance.py`** asserts all of the above.

## [0.3.8] — 2026-10-11

- **ruff and mypy run in CI** (qso-graph-devel#66), as a job the `ci-all-green` gate requires.
  Settings follow `adif-mcp`, the reference for every qso-graph Python repo, rather than a style of
  this repo's own. They run once rather than per Python version: both read the source, and neither
  answer changes with the interpreter.
- Removed an unused `pytest` import from the tests, and typed two functions that promised a `str`
  while returning `Any` from a decoded response.
- `E501` is deferred rather than adopted (qso-graph-devel#70): what it reports in these repos are
  widths, not defects, and some lines are long because they name a publisher's field exactly.
- `mcp.run` is given the literal fastmcp asks for rather than a `str` that happens to hold the
  right word.
- **`fastmcp` is bounded: `>=4.0,<5`** (qso-graph-devel#60). It was `>=3.0` with no upper bound, and
  these servers are run with `uvx`, which resolves fresh — so a `fastmcp` 5.0 would have reached
  every user automatically, before anything here had been run against it. The floor rises to 4.0
  because that is what is actually tested: every lock in the fleet held a 4.x, and nothing in CI
  has ever exercised 3.x. A claim of 3.x support that no test backs is not support.
- `fastmcp` is locked at 4.1.0, the current release, so CI runs against what a new install gets.
- **The published contact is `maintainers@qso-graph.io`** (qso-graph-devel#69). The `authors` field
  carried a personal address, and that field is what PyPI shows on the package page. Everything in
  qso-graph is open source and open to contribution, so the contact is the project's.

## [0.3.7] — 2026-10-07

- LICENSE: the full GPL-3.0 text. The file held only its opening and a link, so GitHub detected no licence.

## [0.3.6] — 2026-10-06

- PyPI: the Documentation link goes to this package's own page, https://qso-graph.io/servers/lotw/ (qso-graph/.github#15).
- CI: the release flow (qso-graph/.github TEMPLATES.md). Work lands on `develop`; a release is a
  PR from `develop` into `main`, and merging it publishes to PyPI and the MCP Registry, verifies both
  and tags the release. CI runs on `develop` too, and PRs into `main` must come from `develop` or a
  `security/` branch.

## [0.3.5] — 2026-10-04

Documentation only; no code changes. Released so the PyPI page shows the corrected README.

### Changed
- README: the credential steps used `qso-auth persona create / provider / secret`, which don't exist. Now `persona add`, `provider enable`, `creds set` (#6).
- README: uvx only, no pip (#5).

## [0.3.4] — 2026-09-28

### Added (CI hygiene)

- **MCP Registry sync** — `publish.yml` publishes to the [Official MCP Registry](https://registry.modelcontextprotocol.io)
  after each PyPI publish, using GitHub OIDC for auth. Triggered on
  `v*` tag push; no manual steps. The Registry job waits until PyPI
  serves the version, and retries. Pattern documented in
  [qso-graph/.github/TEMPLATES.md](https://github.com/qso-graph/.github/blob/main/TEMPLATES.md).
- **Registry version badge** in README — PyPI and Registry versions
  are visible side-by-side so any drift between publishing surfaces
  is immediately apparent.
- **Release gates** — the tag must match `pyproject.toml`, and a
  `verify` job fails the release unless PyPI and the MCP Registry
  both serve the new version.

### Fixed

- The Official MCP Registry listed lotw-mcp at 0.2.0. This release brings it current.

## [0.3.3] — 2026-05-16

### Added
- New tool `get_version_info` — returns `{service_name, service_version, spec_version}`
  for fleet identity attestation. Tracks [IONIS-AI/ionis-devel#49](https://github.com/IONIS-AI/ionis-devel/issues/49).
- `__spec_version__` pinned to `lotw-arrl-v1`.
- L2 unit tests LOTW-L2-043 through LOTW-L2-047.
- `.github/workflows/ci.yml` — PR-gating CI (py3.10-3.13 matrix).

### Changed
- `__init__.py` modernized to fleet pattern (`Final` types).

## [0.3.2] — Previous release
- See git history for changes prior to the changelog being introduced.
