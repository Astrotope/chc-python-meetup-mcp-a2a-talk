# Chess Player Agent

An intelligent chess-playing AI agent built with pydantic.ai that can analyze positions, make strategic moves, and communicate with other agents via MCP and A2A protocols.

## Features

- **AI-Powered Chess Playing**: Uses OpenAI GPT-4 for strategic chess decision making
- **MCP Integration**: Connects to chess MCP server for move validation and execution
- **A2A Protocol**: Agent-to-agent communication for multi-agent chess games
- **Strategic Analysis**: Provides reasoning for chess moves and position evaluation
- **Dockerized**: Ready for containerized deployment

## Quick Start

### Prerequisites

1. OpenAI API key
2. Access to chess MCP server (see ../chess-mcp-server/)
3. Python 3.11+
4. uv package manager

### Setup

1. **Clone and navigate to the directory**:
   ```bash
   cd chess-player-agent
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

4. **Test the agent**:
   ```bash
   uv run python test_agent.py
   ```

### Running the Agent

#### As a standalone test:
```bash
uv run python chess_player_agent.py
```

#### As an A2A server:
```bash
uv run python -c "import asyncio; from chess_player_agent import start_chess_agent_server; asyncio.run(start_chess_agent_server())"
```

#### With Docker:
```bash
docker build -t chess-player-agent .
docker run -e OPENAI_API_KEY=your_key_here chess-player-agent
```

## Configuration

Environment variables can be set in `.env` file:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `CHESS_MCP_SERVER_URL`: Chess MCP server endpoint (default: http://localhost:5000/mcp)
- `AGENT_MODEL`: OpenAI model to use (default: openai:gpt-4)
- `AGENT_NAME`: Agent identifier (default: chess-player-agent)
- `AGENT_PORT`: A2A server port (default: 5001)

## Architecture

### Core Components

- **ChessPlayerAgent**: Main agent class with game state management
- **Chess MCP Integration**: Uses pydantic.ai MCP toolsets to connect to chess server
- **A2A Server**: Converts agent to A2A protocol for multi-agent communication
- **Strategic AI**: GPT-4 powered chess strategy and move analysis

### Agent Capabilities

The agent can:
- Analyze chess positions strategically
- Make legal chess moves with reasoning
- Respond to opponent moves intelligently
- Use Stockfish engine analysis when needed
- Communicate via standardized A2A protocol

### MCP Tools Used

- `validate_move`: Verify move legality
- `make_move`: Execute moves on chess board
- `get_game_status`: Check game state (checkmate, stalemate, etc.)
- `get_stockfish_move`: Get engine analysis for difficult positions
- `health_check`: Verify chess server connectivity

## Development

### Running Tests

```bash
# Unit tests (fast, mocked dependencies)
uv run pytest tests/unit/ -v

# Integration tests (requires MCP server and API key)
uv run pytest tests/integration/ -v -m integration

# All tests
uv run pytest tests/ -v
```

### Test Categories

- **Unit Tests**: Fast tests with mocked dependencies
- **Integration Tests**: Real MCP server and API integration
- **E2E Tests**: Full system tests with multiple agents

### Adding New Features

1. Implement logic in `chess_player_agent.py`
2. Add unit tests in `tests/unit/`
3. Add integration tests in `tests/integration/`
4. Update documentation

## Multi-Agent Integration

The agent exposes an A2A server for communication with other chess agents:

```python
from chess_player_agent import create_a2a_app

# Create A2A server
app = create_a2a_app()

# Agent can now communicate with other A2A agents
```

## API Reference

### ChessPlayerAgent

```python
agent = ChessPlayerAgent(is_white=True)

# Analyze current position
analysis = await agent.analyze_position()

# Make a chess move
response = await agent.make_move("Opening move context")

# Respond to opponent move
response = await agent.respond_to_opponent_move("e7e5")
```

### A2A Server

```python
# Create and start A2A server
app = create_a2a_app()
server_app = await start_chess_agent_server()
```

## Docker Deployment

### Build Image
```bash
docker build -t chess-player-agent .
```

### Run Container
```bash
docker run -d \
  -e OPENAI_API_KEY=your_key_here \
  -e CHESS_MCP_SERVER_URL=http://chess-mcp-server:5000/mcp \
  -p 5001:5001 \
  chess-player-agent
```

### With Docker Compose
```yaml
services:
  chess-player-agent:
    build: .
    environment:
      - OPENAI_API_KEY=your_key_here
      - CHESS_MCP_SERVER_URL=http://chess-mcp-server:5000/mcp
    ports:
      - "5001:5001"
    depends_on:
      - chess-mcp-server
```

## Troubleshooting

### Common Issues

1. **API Key Issues**: Ensure `OPENAI_API_KEY` is set correctly
2. **MCP Server Unavailable**: Verify chess MCP server is running and accessible
3. **Docker Networking**: Use container names for inter-service communication
4. **Rate Limits**: OpenAI API has rate limits; consider implementing backoff

### Debugging

Enable verbose logging:
```bash
export LOG_LEVEL=DEBUG
uv run python chess_player_agent.py
```

Check health:
```bash
curl http://localhost:5001/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.