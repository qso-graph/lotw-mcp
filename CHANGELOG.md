# Changelog

All notable changes to `lotw-mcp` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] — 2026-10-27

### Added

- **A `429` from LoTW is now honoured.** LoTW asking this client to
  stop is the most explicit form a request limit takes, and it was previously
  ignored: the error was reported and the next tool call sent another request.
  Now the `Retry-After` interval is read and bounded to between a minute and an
  hour, no further call goes out until it has passed, and the tool says how long
  to wait. It does not sleep through the wait — a tool call is synchronous and an
  hour's sleep inside one is a hang, so it refuses quickly and says when to come
  back. A `503` is treated as an outage unless it carries `Retry-After`, in which
  case it is a deliberate shed and honoured the same way.


## [Unreleased]

### Changed

- **Requests to ARRL Logbook of The World are now spaced.** Where a provider states a request
  limit this server honours that limit; ARRL Logbook of The World states none, so the gap is a
  recorded judgement rather than a published figure — 200 ms, matching what
  `sota-mcp` and `iota-mcp` already use, with the reasoning written beside the
  constant so it can be revisited rather than rediscovered. A volunteer or public
  service with no stated limit still deserves restraint (KI7MT, 2026-10-11).

  This is not throttling the user. It limits what this server sends to somebody
  else's service; it does not limit the person asking. The response cache does the
  larger share of the work by removing requests rather than delaying them, and the
  spacing covers what a cache cannot: a model calling tools in a loop over inputs
  that each miss.


## [0.5.0] — 2026-10-26

### Changed

- **Python 3.11 is the minimum.** 3.10 reached end of life in October 2026
  ([PEP 619](https://peps.python.org/pep-0619/)), so it gets no further security
  releases on any platform. On Windows it was worse than unsupported: `uv`'s 3.10
  is built against OpenSSL 1.1.1w, end of life since September 2023, so HTTPS
  from this server ran over an unmaintained TLS library. `certifi` does not help
  with that — it supplies the root store, not the implementation.

  3.10 support was already nominal. This package has linted with
  `ruff target-version = "py311"` and type-checked with `mypy python_version =
  "3.11"` for some time, so nothing ever verified the 3.10 claim.

  `uv.lock` is regenerated and the diff is large, but **nothing is upgraded** —
  it is the 3.10 resolution branch disappearing. Packages that carried two pins,
  one per Python branch, now carry the single 3.11+ pin they already resolved to.
  An install on 3.11 or later is unchanged.

## [0.4.3] — 2026-10-26

### Changed

- `--transport streamable-http` now says where it bound, and the help text says
  it too. It binds `127.0.0.1`, and FastMCP takes no host option, so it was
  never reachable from another machine or from outside a container — and nothing
  said so. The bind address is unchanged: loopback-only is deliberate for a
  server that holds credentials and has no authentication of its own.

## [0.4.2] — 2026-10-26

### Fixed

- `--version` and `--help` now print and exit. They were ignored, so the
  command started the MCP server on stdio and waited for JSON-RPC — leaving a
  FastMCP banner on screen and an apparently hung terminal. Seven servers in
  this fleet already behaved correctly; this brings the rest in line, and a
  test asserts it.

## [0.4.1] — 2026-10-26

- A release should appear on the Releases page
- Move every Node 20 action to its first Node 24 major
- The locked-dependency audit blocked every release
- Four upgrades arrived as 57 pull requests
- Nothing was auditing the lockfile
- Close every open security advisory in the lockfile
- A release is a workflow, not a merge
- Make the publish gate's http:// check portable
- Assert that certifi is declared, not merely imported

## [0.4.0] — 2026-10-12

**Upgrading:** a tool that fails now returns `isError: true` instead of a successful result whose
payload contained an `error` key. Anything reading `result["error"]` should read the error flag.
LoTW's own verdict is still passed on — `Login failed` is what a model should see.

**Security-relevant:** LoTW's error pages are HTML ARRL controls, and this server's requests put the
password in the query string. A page echoing the request used to carry the password into the
message. That text is now withheld, with a reason, when it contains the secret or any URL.


- **`E501` is adopted** (#22, qso-graph-devel#70). It reported **four lines, none of them a
  defect**. Two reflowed.
- The other two are **ADIF records in the sample LoTW responses**, and an ADIF record is written on
  one line. Checked rather than asserted: this project's parser is *not* line-based, and wrapping a
  record between fields parses identically — so the exemption is not "wrapping would break it" but
  that a wrapped sample stops resembling what LoTW actually sends, which is the only reason those
  samples exist. The same ground as `solar-mcp` keeping NOAA's alert text intact.
- Those samples moved to **`_mock_adif.py`**, which carries a file-level `# ruff: noqa: E501` and
  the reason. That confines the exemption to a file holding nothing but sample data; a
  `per-file-ignores` entry on `client.py` would have exempted several hundred lines of real code
  for the sake of two lines of ADIF. The move is behaviour-neutral and the suite is unchanged.

- **`certifi` is carried, and both fetch paths verify against it** (#21, qso-graph-devel#73). They
  used `urllib` with no context, so they trusted whichever root store the running Python was built
  against. On macOS that is `/etc/ssl/cert.pem`, a deliberately *reduced* OpenSSL file — 128 roots
  against the system keychain's 158, and current rather than stale. **lotw.arrl.org verifies fine
  against it today**, so this was latent rather than an outage.
- **It matters more here than in most of the fleet: the operator's LoTW password travels over these
  connections**, in query parameters, because that is how LoTW's query interface works. Which is
  why verification is never disabled — `ssl.CERT_NONE` would make a failing call "work" by
  accepting any certificate from anyone, and here that means handing the password to whoever
  presented it.
- The context lives in its own module, `_tls.py`, because the calls are in **two** files —
  `client.py` and `user_activity.py`. A context defined in one and imported by the other would
  couple them for no reason, and the guard has one thing to point at.
- **The "every `urlopen` verifies" check scans the whole package, not one file.** That is the
  difference that matters here: a check reading only `client.py` would have missed
  `user_activity.py` entirely — which is how a server ends up verifying on the path that carries
  the password and not on the other one. Reverting exactly that is what the falsification drives.
- **`tests/test_release_gate.py`** asserts the gate suite imports nothing but the standard library
  and pytest. solar-mcp's 0.3.0 publish failed on exactly that, from the same change.

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
