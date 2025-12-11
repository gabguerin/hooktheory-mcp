# Hooktheory MCP Server

A Model Context Protocol (MCP) server that enables AI agents to interact with the Hooktheory API for chord progression generation, song analysis, and music theory data retrieval.

## Quick Start

Get up and running in 3 simple steps:

1. **Get your API key** from [Hooktheory API](https://www.hooktheory.com/api/trends/docs)

2. **Install and run:**
   ```bash
   export HOOKTHEORY_API_KEY="your-api-key-here"
   uvx hooktheory-mcp
   ```

3. **Try these examples with your AI assistant:**
   - "Find songs with the chord progression I-V-vi-IV"
   - "Analyze the song 'Wonderwall' by Oasis"
   - "Show me popular chord progressions in C major"
   - "Find songs similar to 'Let It Be' by The Beatles"

That's it! Your AI can now access music theory data and chord progressions.

## Common Usage Examples

### Search for Songs by Chord Progression
```
Find songs using the progression 1,5,6,4 in the key of C major
```

### Analyze Any Song
```
What are the chords in "Someone Like You" by Adele?
```

### Discover Popular Progressions
```
What are the most common chord progressions in pop music?
```

### Find Similar Songs
```
Find songs that have similar chord progressions to "Hotel California"
```

## Features

The server provides the following tools for music analysis and generation:

- **Chord Progression Search**: Find songs with specific chord progressions
- **Song Analysis**: Analyze specific songs to get chord progressions and key information
- **Popular Progressions**: Discover the most popular chord progressions
- **Similar Songs**: Find songs with similar chord progressions
- **Progression Generation**: Generate chord progressions based on music theory patterns

## Installation

### Prerequisites

- Python 3.11 or higher
- A Hooktheory API key (Get one at https://www.hooktheory.com/api/trends/docs)

### Setup

1. **Install with uvx (recommended):**
   ```bash
   uvx hooktheory-mcp
   ```

2. **Or install from source:**
   ```bash
   git clone <repository-url>
   cd hooktheory-mcp
   uv sync
   ```

3. **Set up your API key:**
   ```bash
   export HOOKTHEORY_API_KEY="your-api-key-here"
   ```

   Or create a `.env` file:
   ```
   HOOKTHEORY_API_KEY=your-api-key-here
   ```

4. **Test the installation:**
   ```bash
   uvx hooktheory-mcp --help
   # Or if installed from source:
   uv run hooktheory-mcp --help
   ```

## Usage

### Command Line

The server can be run in different modes:

**Standard MCP mode (stdio transport):**
```bash
uvx hooktheory-mcp
# Or from source: uv run hooktheory-mcp
```

**Streamable HTTP mode for web integration:**
```bash
uvx hooktheory-mcp --transport streamable-http
# Or from source: uv run hooktheory-mcp --transport streamable-http
```

**Server-Sent Events (SSE) mode:**
```bash
uvx hooktheory-mcp --transport sse
# Or from source: uv run hooktheory-mcp --transport sse
```

### MCP Client Configuration

For Claude Desktop, add this to your configuration:

```json
{
  "mcpServers": {
    "hooktheory": {
      "command": "uvx",
      "args": ["hooktheory-mcp"],
      "env": {
        "HOOKTHEORY_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Alternative for development/local install:**
```json
{
  "mcpServers": {
    "hooktheory": {
      "command": "uv",
      "args": ["run", "hooktheory-mcp"],
      "cwd": "/path/to/hooktheory-mcp",
      "env": {
        "HOOKTHEORY_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## Available Tools

### 1. `get_chord_progressions`
Search for songs with specific chord progressions.

**Parameters:**
- `cp` (required): Chord progression in Roman numeral notation (e.g., "1,5,6,4")
- `key` (optional): Musical key (e.g., "C", "Am")
- `mode` (optional): Scale mode ("major", "minor")
- `artist` (optional): Filter by artist name
- `song` (optional): Filter by song title

**Example:**
```
Find songs with the progression I-V-vi-IV in the key of C major
```

### 2. `analyze_song`
Analyze a specific song to get its chord progression and music theory data.

**Parameters:**
- `artist` (required): Artist name
- `song` (required): Song title

**Example:**
```
Analyze "Wonderwall" by Oasis
```

### 3. `get_popular_progressions`
Get the most popular chord progressions from the database.

**Parameters:**
- `key` (optional): Filter by musical key
- `mode` (optional): Filter by scale mode
- `limit` (optional): Max results (default: 20)

**Example:**
```
Show me the most popular chord progressions in C major
```

### 4. `find_similar_songs`
Find songs with similar chord progressions to a reference song.

**Parameters:**
- `artist` (required): Reference artist name
- `song` (required): Reference song title
- `similarity_threshold` (optional): Similarity score 0.0-1.0 (default: 0.7)

**Example:**
```
Find songs similar to "Let It Be" by The Beatles
```

### 5. `generate_progression`
Generate chord progressions based on music theory patterns.

**Parameters:**
- `key` (optional): Starting key (default: "C")
- `mode` (optional): Scale mode (default: "major")
- `length` (optional): Number of chords (default: 4)
- `style` (optional): Musical style hint ("pop", "rock", "jazz")

**Example:**
```
Generate a 4-chord pop progression in A minor
```

## API Integration

The server integrates with the Hooktheory API endpoints:

- **Base URL**: `https://www.hooktheory.com/api/trends`
- **Authentication**: Bearer token via `Authorization` header
- **Rate Limiting**: Follows Hooktheory API limits

## Development

### Project Structure
```
hooktheory-mcp/
├── src/hooktheory_mcp/
│   └── __init__.py          # Main MCP server implementation
├── pyproject.toml           # Project configuration
├── uv.lock                  # Dependency lock file
└── README.md               # This file
```

### Adding New Tools

To add new tools, edit `src/hooktheory_mcp/__init__.py` and add new functions decorated with `@mcp.tool()`:

```python
@mcp.tool()
async def your_new_tool(param1: str, param2: Optional[int] = None) -> str:
    """
    Description of your tool.

    Args:
        param1: Description of parameter
        param2: Optional parameter description

    Returns:
        Description of return value
    """
    # Implementation here
    return result
```

### Testing

```bash
# Run basic connectivity test
uv run python -c "
import asyncio
from hooktheory_mcp import hooktheory_client
asyncio.run(hooktheory_client._make_request('test'))
"
```

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```
   Error: HOOKTHEORY_API_KEY environment variable is required
   ```
   Solution: Set the `HOOKTHEORY_API_KEY` environment variable

2. **HTTP 401 Unauthorized**
   ```
   HTTP error calling https://www.hooktheory.com/api/trends/...: 401
   ```
   Solution: Verify your API key is correct and active

3. **Connection Errors**
   ```
   HTTP error calling https://www.hooktheory.com/api/trends/...: ConnectError
   ```
   Solution: Check internet connection and Hooktheory API status

### Debug Mode

Enable debug logging:
```bash
export PYTHONPATH=src
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from hooktheory_mcp import main
main()
"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- [Hooktheory API Documentation](https://www.hooktheory.com/api/trends/docs)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)