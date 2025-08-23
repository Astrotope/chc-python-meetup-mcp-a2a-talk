# Standalone MCP Server with Python A2A and uv

## Overview

This document outlines how to create a standalone MCP server using Python A2A's FastMCP implementation, based on the `start_mcp_server` function pattern and containerization with uv package management.

## Core Implementation Pattern

### MCP Server Structure

The `start_mcp_server` function from python-a2a demonstrates a clean pattern for creating standalone MCP servers:

```python
from python_a2a import FastMCP

# Create FastMCP instance
utility_mcp = FastMCP(name="utility-server")

@utility_mcp.tool
def calculator(operation: str, num1: float, num2: float) -> str:
    """Perform mathematical operations on two numbers."""
    try:
        if operation.lower() == "add":
            result = num1 + num2
        elif operation.lower() == "subtract":
            result = num1 - num2
        elif operation.lower() == "multiply":
            result = num1 * num2
        elif operation.lower() == "divide":
            if num2 == 0:
                return "Error: Division by zero is not allowed."
            result = num1 / num2
        else:
            return f"Error: Unknown operation '{operation}'"
        
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@utility_mcp.tool
def unit_converter(value: float, from_unit: str, to_unit: str, unit_type: str) -> str:
    """Convert between different units of measurement."""
    # Normalize units (remove plurals)
    from_unit = from_unit.rstrip('s').lower()
    to_unit = to_unit.rstrip('s').lower()
    
    try:
        if unit_type.lower() == "temperature":
            # Temperature conversions
            if from_unit == "celsius" and to_unit == "fahrenheit":
                result = (value * 9/5) + 32
            elif from_unit == "fahrenheit" and to_unit == "celsius":
                result = (value - 32) * 5/9
            elif from_unit == "celsius" and to_unit == "kelvin":
                result = value + 273.15
            elif from_unit == "kelvin" and to_unit == "celsius":
                result = value - 273.15
            else:
                return f"Conversion from {from_unit} to {to_unit} not supported"
        
        elif unit_type.lower() == "distance":
            # Distance conversions (convert to meters first, then to target)
            meter_conversions = {
                "meter": 1, "kilometer": 1000, "centimeter": 0.01,
                "mile": 1609.34, "foot": 0.3048, "inch": 0.0254
            }
            
            if from_unit in meter_conversions and to_unit in meter_conversions:
                meters = value * meter_conversions[from_unit]
                result = meters / meter_conversions[to_unit]
            else:
                return f"Conversion from {from_unit} to {to_unit} not supported"
        
        elif unit_type.lower() == "weight":
            # Weight conversions (convert to grams first, then to target)
            gram_conversions = {
                "gram": 1, "kilogram": 1000, "pound": 453.592,
                "ounce": 28.3495, "ton": 1000000
            }
            
            if from_unit in gram_conversions and to_unit in gram_conversions:
                grams = value * gram_conversions[from_unit]
                result = grams / gram_conversions[to_unit]
            else:
                return f"Conversion from {from_unit} to {to_unit} not supported"
        
        else:
            return f"Unit type '{unit_type}' not supported"
        
        return f"{value} {from_unit} = {result:.4f} {to_unit}"
    
    except Exception as e:
        return f"Error: {str(e)}"

def start_mcp_server():
    """Start the MCP server."""
    utility_mcp.run()

if __name__ == "__main__":
    start_mcp_server()
```

### Key Implementation Patterns from Examples

1. **Tool Registration**: Use `@mcp.tool` decorator for each function
2. **Error Handling**: Comprehensive try-catch blocks with user-friendly messages
3. **Type Annotations**: Clear parameter and return types for tool interfaces
4. **Descriptive Documentation**: Docstrings become tool descriptions in MCP
5. **Flexible Logic**: Support multiple operations within single tools
6. **Fallback Handling**: Default responses for unknown inputs

## Chess MCP Server Implementation

For our chess system, we would create a specialized MCP server:

```python
from python_a2a import FastMCP
import chess
import chess.engine
from datetime import datetime
import os

# Create chess-specific MCP server
chess_mcp = FastMCP(name="chess-server")

@chess_mcp.tool
def is_move_valid_given_fen(fen: str, move_uci: str) -> dict:
    """Check if a move is valid given a board position."""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        is_legal = move in board.legal_moves
        return {"valid": is_legal, "error": None}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@chess_mcp.tool
def make_move(fen: str, move_uci: str) -> dict:
    """Execute a move on the board and return new position."""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
            return {
                "new_fen": board.fen(),
                "success": True,
                "error": None
            }
        else:
            return {
                "new_fen": fen,
                "success": False,
                "error": "Invalid move"
            }
    except Exception as e:
        return {
            "new_fen": fen,
            "success": False,
            "error": str(e)
        }

@chess_mcp.tool
def get_stockfish_move(fen: str, time_limit: float = 1.0) -> dict:
    """Get best move from Stockfish engine."""
    try:
        board = chess.Board(fen)
        stockfish_path = os.environ.get("STOCKFISH_PATH", "/usr/games/stockfish")
        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            result = engine.play(board, chess.engine.Limit(time=time_limit))
            return {
                "move_uci": result.move.uci() if result.move else None,
                "success": True,
                "error": None
            }
    except Exception as e:
        return {
            "move_uci": None,
            "success": False,
            "error": str(e)
        }

@chess_mcp.tool
def get_game_status(fen: str) -> dict:
    """Check game status including checkmate, stalemate, and draw conditions."""
    try:
        board = chess.Board(fen)
        outcome = board.outcome()
        
        return {
            "is_game_over": outcome is not None,
            "winner": str(outcome.winner) if outcome and outcome.winner else None,
            "termination": str(outcome.termination) if outcome else None,
            "is_check": board.is_check(),
            "legal_moves_count": len(list(board.legal_moves)),
            "error": None
        }
    except Exception as e:
        return {
            "is_game_over": False,
            "winner": None,
            "termination": None,
            "is_check": False,
            "legal_moves_count": 0,
            "error": str(e)
        }

def start_chess_mcp_server():
    """Start the chess MCP server."""
    print(f"Starting chess MCP server at {datetime.now()}")
    chess_mcp.run()

if __name__ == "__main__":
    start_chess_mcp_server()
```

## Docker Containerization with uv

### Dockerfile Structure

Based on the existing Dockerfile pattern using uv:

```dockerfile
# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies including Stockfish and curl for uv installation
RUN apt-get update && apt-get install -y \
    stockfish \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy uv files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose port for MCP server
EXPOSE 8000

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STOCKFISH_PATH="/usr/games/stockfish"

# Run the chess MCP server with uv
CMD ["uv", "run", "chess_mcp_server.py"]

# Create a non-root user for security
RUN useradd -m chessuser
USER chessuser
```

### pyproject.toml Configuration

```toml
[project]
name = "chess-mcp-server"
version = "0.1.0"
description = "Standalone MCP server for chess operations"
requires-python = ">=3.10"
dependencies = [
    "python-a2a>=0.1.0",
    "python-chess>=1.999",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 88
target-version = "py310"

[tool.black]
line-length = 88
target-version = ['py310']
```

### Key Differences from Template Dockerfile

1. **Package Manager**: Uses `uv sync --frozen` instead of `pip install -r requirements.txt`
2. **Dependency Files**: Uses `pyproject.toml` and `uv.lock` instead of `requirements.txt`
3. **Runtime**: Uses `uv run` instead of direct python execution or uvicorn
4. **Caching**: Copy uv files first for better Docker layer caching
5. **Environment**: Maintains same environment variables for consistency

## Environment Configuration

### Environment Variables

```bash
# Server configuration
MCP_SERVER_PORT=8000
MCP_SERVER_HOST=0.0.0.0

# Chess engine configuration
STOCKFISH_PATH=/usr/games/stockfish
STOCKFISH_THREADS=1
STOCKFISH_MEMORY=128

# Logging
LOG_LEVEL=INFO
LOG_FILE=/usr/src/app/logs/chess-mcp.log

# Python environment
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  chess-mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - STOCKFISH_PATH=/usr/games/stockfish
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/usr/src/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Health Checks and Monitoring

```python
@chess_mcp.tool
def health_check() -> dict:
    """Check server health and chess engine availability."""
    try:
        # Test basic chess functionality
        board = chess.Board()
        legal_moves = len(list(board.legal_moves))
        
        # Test Stockfish availability
        stockfish_path = os.environ.get("STOCKFISH_PATH", "/usr/games/stockfish")
        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            engine_info = str(engine.id)
        
        return {
            "status": "healthy",
            "chess_engine": "available",
            "engine_info": engine_info[:100],  # Limit length
            "legal_moves_test": legal_moves == 20,  # Standard starting position
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

## uv Specific Optimizations

### Multi-stage Build for Production

```dockerfile
# Build stage
FROM python:3.10-slim as builder

WORKDIR /usr/src/app

# Install curl for uv installation
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy uv files and sync dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Production stage
FROM python:3.10-slim

WORKDIR /usr/src/app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y stockfish && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /usr/src/app/.venv /usr/src/app/.venv

# Copy application code
COPY . .

# Set environment variables
ENV PATH="/usr/src/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STOCKFISH_PATH="/usr/games/stockfish"

# Create non-root user
RUN useradd -m chessuser
USER chessuser

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "chess_mcp_server.py"]
```

## Integration with A2A Agents

```python
# In A2A agent code
from python_a2a import FastMCPAgent

class ChessPlayerAgent(FastMCPAgent):
    def __init__(self, color: str, mcp_server_url: str = "http://chess-mcp-server:8000"):
        super().__init__(
            mcp_servers={
                "chess": mcp_server_url
            }
        )
        self.color = color
    
    async def make_move(self, fen: str):
        """Make a move using the external MCP chess server."""
        try:
            # Get engine suggestion
            result = await self.call_mcp_tool(
                "chess", 
                "get_stockfish_move", 
                {"fen": fen, "time_limit": 2.0}
            )
            
            if result["success"]:
                # Execute the move
                move_result = await self.call_mcp_tool(
                    "chess",
                    "make_move",
                    {"fen": fen, "move_uci": result["move_uci"]}
                )
                return move_result
            else:
                return {"success": False, "error": "No move found"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_move(self, fen: str, move_uci: str):
        """Validate a move using the external MCP chess server."""
        return await self.call_mcp_tool(
            "chess",
            "is_move_valid_given_fen",
            {"fen": fen, "move_uci": move_uci}
        )
```

## Development and Testing

### Local Development with uv

```bash
# Install dependencies
uv sync

# Run in development mode
uv run chess_mcp_server.py

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check .
```

### Testing Strategy

```python
# tests/test_chess_mcp.py
import pytest
import asyncio
from python_a2a import FastMCP
from chess_mcp_server import chess_mcp

@pytest.mark.asyncio
async def test_move_validation():
    """Test move validation tool."""
    result = await chess_mcp.call_tool(
        "is_move_valid_given_fen",
        {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "move_uci": "e2e4"
        }
    )
    assert result["valid"] is True
    assert result["error"] is None

@pytest.mark.asyncio 
async def test_stockfish_integration():
    """Test Stockfish engine integration."""
    result = await chess_mcp.call_tool(
        "get_stockfish_move",
        {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "time_limit": 1.0
        }
    )
    assert result["success"] is True
    assert result["move_uci"] is not None
```

This standalone MCP server pattern with uv provides an efficient, containerized solution for chess engine integration within the A2A multi-agent architecture.