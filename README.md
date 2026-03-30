# Point MCP Server

MCP server for the [Point Knowledge API](https://pinchpoint.dev/point) — verified, citable knowledge for AI coding assistants.

Point indexes curated technical documentation (RFCs, framework docs, standards, API references) and makes it searchable with hybrid search (BM25 + vector) and precise citations. This MCP server gives your AI assistant direct access to that knowledge.

## Tools

| Tool | Description | Tokens |
|------|-------------|--------|
| `search` | Hybrid search with citations and relevance scores | ~200/result |
| `get_document_toc` | Lightweight table of contents for a document | ~50 |
| `get_sections` | Load specific sections by chunk ID (max 50) | varies |
| `list_collections` | Browse or search available knowledge collections | ~100/collection |
| `get_document_full` | Full markdown content of a document | varies (can be large) |

**Recommended workflow:** `search` or `list_collections` to find content, then `get_document_toc` for structure, then `get_sections` for specific passages. Use `get_document_full` only when you need the complete text.

## Prerequisites

1. **Python 3.11+** installed
2. **Point API key** — get one free at [pinchpoint.dev/point/keys](https://pinchpoint.dev/point/keys)

## Installation

```bash
pip install point-mcp
```

Or install from source:

```bash
git clone https://github.com/mcdonaldsam/point-mcp.git
cd point-mcp
pip install -e .
```

## Setup by IDE

### Claude Code

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "point": {
      "command": "point-mcp",
      "env": {
        "POINT_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Or add via CLI:

```bash
claude mcp add point -- point-mcp -e POINT_API_KEY=your-api-key-here
```

### Cursor

Add to your Cursor MCP config (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "point": {
      "command": "point-mcp",
      "env": {
        "POINT_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Windsurf

Add to your Windsurf MCP config (`~/.windsurf/mcp.json`):

```json
{
  "mcpServers": {
    "point": {
      "command": "point-mcp",
      "env": {
        "POINT_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### VS Code (GitHub Copilot)

Add to your VS Code settings (`.vscode/mcp.json` in your project, or user settings):

```json
{
  "servers": {
    "point": {
      "type": "stdio",
      "command": "point-mcp",
      "env": {
        "POINT_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Using uvx (no install needed)

If you have `uv` installed, you can run point-mcp without installing it globally:

```json
{
  "mcpServers": {
    "point": {
      "command": "uvx",
      "args": ["point-mcp"],
      "env": {
        "POINT_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Manual / Other Tools

Any MCP client that supports stdio transport:

```bash
POINT_API_KEY=your-api-key-here point-mcp
```

## Configuration

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `POINT_API_KEY` | Yes | — | Your Point API key ([get one](https://pinchpoint.dev/point/keys)) |
| `POINT_API_URL` | No | `https://point-api.pinchpoint.dev` | API base URL (for self-hosted or local dev) |

## Examples

Once configured, your AI assistant can use Point tools naturally:

> "Search Point for how OAuth 2.0 PKCE works"

> "What collections does Point have about cloud infrastructure?"

> "Get the table of contents for document rfc-7636, then load sections 2 and 3"

The assistant will automatically use the appropriate tools and include citations in its responses.

## Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/mcdonaldsam/point-mcp.git
cd point-mcp
pip install -e ".[dev]"

# Run tests
pytest

# Run server locally
POINT_API_KEY=your-key point-mcp
```

## License

MIT
