# Chess MCP Server

A minimal MCP (Model Context Protocol) server providing chess functionality through Stockfish integration.

## Features

- **Move Validation**: Check if moves are legal for a given board position
- **Move Execution**: Execute moves and return updated board state
- **Engine Analysis**: Get best moves from Stockfish engine
- **Game Status**: Check for checkmate, stalemate, and draw conditions
- **Health Monitoring**: Server and engine health checks

## Requirements

- Python 3.10+
- uv (for dependency management)
- Stockfish chess engine

## Installation

### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install Stockfish (Ubuntu/Debian)
sudo apt-get install stockfish

# Or on macOS
brew install stockfish
```

## Usage

### Local Development

```bash
# Set Stockfish path (if not in default location)
export STOCKFISH_PATH=/path/to/stockfish

# Run the server
uv run chess_mcp_server.py
```

### Docker

```bash
# Build the image
docker build -t chess-mcp-server .

# Run the container
docker run -p 8003:8003 chess-mcp-server
```

## Available MCP Tools

### `validate_move(fen: str, move_uci: str)`
Check if a move is valid for the given board position.

**Parameters:**
- `fen`: Board position in FEN notation
- `move_uci`: Move in UCI notation (e.g., "e2e4")

**Returns:**
```json
{
  "valid": true,
  "error": null
}
```

### `make_move(fen: str, move_uci: str)`
Execute a move and return the new board state.

**Parameters:**
- `fen`: Current board position in FEN notation
- `move_uci`: Move to execute in UCI notation

**Returns:**
```json
{
  "success": true,
  "new_fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "error": null
}
```

### `get_stockfish_move(fen: str, time_limit: float = 2.0)`
Get the best move from Stockfish for the given position.

**Parameters:**
- `fen`: Board position in FEN notation
- `time_limit`: Time limit for engine analysis in seconds (default: 2.0)

**Returns:**
```json
{
  "success": true,
  "move_uci": "e2e4",
  "error": null
}
```

### `get_game_status(fen: str)`
Check the current game status and conditions.

**Parameters:**
- `fen`: Board position in FEN notation

**Returns:**
```json
{
  "is_game_over": false,
  "winner": null,
  "termination": null,
  "is_check": false,
  "legal_moves_count": 20,
  "current_turn": "white",
  "error": null
}
```

### `health_check()`
Check server and engine health.

**Returns:**
```json
{
  "status": "healthy",
  "chess_engine": "available",
  "engine_info": "Stockfish 15.1 64 POPCNT by the Stockfish developers",
  "legal_moves_test": true,
  "stockfish_path": "/usr/games/stockfish",
  "timestamp": "2024-01-01T12:00:00.000000"
}
```

## Environment Variables

- `STOCKFISH_PATH`: Path to Stockfish executable (default: `/usr/games/stockfish`)
- `MCP_SERVER_HOST`: Server host (default: `0.0.0.0`)
- `MCP_SERVER_PORT`: Server port (default: `8003`)
- `DEFAULT_TIME_LIMIT`: Default engine time limit in seconds (default: `2.0`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Testing

```bash
# Run basic tests
uv run pytest

# Test server health
uv run python -c "from chess_mcp_server import health_check; print(health_check())"
```

## Integration

This MCP server can be integrated with:
- A2A agents using FastMCPAgent
- Other MCP-compatible clients
- Web applications via HTTP/WebSocket
- Multi-agent chess systems

## License

MIT