# lotw-mcp

MCP server for [ARRL Logbook of The World](https://lotw.arrl.org/) (LoTW) — query confirmations, uploaded QSOs, DXCC credits, and user activity through any MCP-compatible AI assistant.

Part of the [qso-graph](https://qso-graph.io/) project. Read-only — uploads require TQSL digital signatures and are out of scope.

## Install

```bash
pip install lotw-mcp
```

## Tools

| Tool | Auth | Description |
|------|------|-------------|
| `lotw_confirmations` | Yes | Query confirmed QSLs with band/mode/call/date filters |
| `lotw_qsos` | Yes | Query all uploaded QSOs (confirmed and unconfirmed) |
| `lotw_dxcc_credits` | Yes | DXCC award credits from LoTW confirmations |
| `lotw_user_activity` | No | Check if a callsign uses LoTW and when they last uploaded |

## Quick Start

### 1. Set up credentials

lotw-mcp uses adif-mcp personas for credential management:

```bash
pip install adif-mcp

adif-mcp persona create ki7mt --callsign KI7MT
adif-mcp persona provider ki7mt lotw --username KI7MT
adif-mcp persona secret ki7mt lotw
```

**Note**: The LoTW `login` is usually your callsign but not always. Pre-Sept 2019 accounts may require lowercase passwords. Avoid special characters in passwords.

### 2. Configure your MCP client

#### Claude Desktop

Add to `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude\` on Windows):

```json
{
  "mcpServers": {
    "lotw": {
      "command": "lotw-mcp"
    }
  }
}
```

#### Claude Code

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "lotw": {
      "command": "lotw-mcp"
    }
  }
}
```

#### ChatGPT Desktop

```json
{
  "mcpServers": {
    "lotw": {
      "command": "lotw-mcp"
    }
  }
}
```

#### Cursor

Add to `.cursor/mcp.json` (project-level) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "lotw": {
      "command": "lotw-mcp"
    }
  }
}
```

#### VS Code / GitHub Copilot

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "lotw": {
      "command": "lotw-mcp"
    }
  }
}
```

#### Gemini CLI

Add to `~/.gemini/settings.json` (global) or `.gemini/settings.json` (project):

```json
{
  "mcpServers": {
    "lotw": {
      "command": "lotw-mcp"
    }
  }
}
```

### 3. Ask questions

> "How many LoTW confirmations did I get this month?"

> "Show me all unconfirmed 20m FT8 QSOs uploaded to LoTW in the last 90 days"

> "What DXCC credits do I have on 40m CW?"

> "Does JA1ABC use LoTW? When did they last upload?"

## Public Tool

`lotw_user_activity` works without any credentials. It uses the public LoTW user activity CSV, cached locally for 7 days.

## Testing Without Credentials

Set the mock environment variable:

```bash
LOTW_MCP_MOCK=1 lotw-mcp
```

## Performance Notes

LoTW can be slow (30-60s for large queries). lotw-mcp uses 120s timeouts. Use date filters (`since`, `start_date`) to limit result sets.

## MCP Inspector

```bash
lotw-mcp --transport streamable-http --port 8004
```

## Development

```bash
git clone https://github.com/qso-graph/lotw-mcp.git
cd lotw-mcp
pip install -e .
```

## License

GPL-3.0-or-later
