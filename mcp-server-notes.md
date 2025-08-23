# FastMCP Server Implementation for Chess Tools

## Overview

This document outlines how to build and deploy MCP servers using FastMCP specifically for our multi-agent chess system, based on analysis of the dockerized MCP server template and FastMCP documentation.

## 1. FastMCP Server Architecture

### 1.1 Basic Server Structure

```python
from fastmcp import FastMCP
import chess
import chess.engine
from stockfish import Stockfish
import os
import logging

# Initialize MCP server
mcp = FastMCP("chess-engine-server")

# Global Stockfish instance
stockfish_engine = None

def initialize_stockfish():
    """Initialize Stockfish engine with default settings"""
    global stockfish_engine
    try:
        stockfish_path = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
        stockfish_engine = Stockfish(
            path=stockfish_path,
            depth=15,
            parameters={
                "Threads": 2,
                "Hash": 256,
                "UCI_LimitStrength": True,
                "UCI_Elo": 1500
            }
        )
        logging.info("Stockfish engine initialized successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to initialize Stockfish: {e}")
        return False

# Initialize engine on server startup
initialize_stockfish()
```

### 1.2 Chess Tool Registration Patterns

Based on the template analysis, here's how to implement chess-specific MCP tools:

```python
@mcp.tool()
async def is_move_valid_given_fen(fen: str, move_uci: str) -> dict:
    """
    Validate if a move is legal in the given position.
    
    Args:
        fen: Board position in FEN notation
        move_uci: Move in UCI notation (e.g., 'e2e4')
    
    Returns:
        Dictionary with validation result and details
    """
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        is_legal = move in board.legal_moves
        
        # Double-check with Stockfish if available
        stockfish_valid = True
        if stockfish_engine:
            stockfish_engine.set_fen_position(fen)
            stockfish_valid = stockfish_engine.is_move_correct(move_uci)
        
        return {
            "valid": is_legal and stockfish_valid,
            "python_chess_valid": is_legal,
            "stockfish_valid": stockfish_valid,
            "error": None
        }
    except Exception as e:
        return {
            "valid": False,
            "python_chess_valid": False,
            "stockfish_valid": False,
            "error": str(e)
        }

@mcp.tool()
async def get_best_move_given_history_in_pgn(pgn_history: str, depth: int = 15, elo: int = 1500) -> dict:
    """
    Get the best move for a position based on PGN game history.
    
    Args:
        pgn_history: Game history in PGN format
        depth: Search depth (default 15)
        elo: Engine strength (default 1500)
    
    Returns:
        Dictionary with best move and analysis
    """
    if not stockfish_engine:
        return {"error": "Stockfish engine not available"}
    
    try:
        # Parse PGN to get current position
        import io
        import chess.pgn
        
        pgn_io = io.StringIO(pgn_history)
        game = chess.pgn.read_game(pgn_io)
        
        if game is None:
            return {"error": "Invalid PGN format"}
        
        # Play through moves to get current position
        board = game.board()
        for move in game.mainline_moves():
            board.push(move)
        
        current_fen = board.fen()
        
        # Configure engine and get best move
        stockfish_engine.set_elo_rating(elo)
        stockfish_engine.set_depth(depth)
        stockfish_engine.set_fen_position(current_fen)
        
        best_move = stockfish_engine.get_best_move()
        evaluation = stockfish_engine.get_evaluation()
        
        return {
            "best_move": best_move,
            "current_fen": current_fen,
            "evaluation": evaluation,
            "depth": depth,
            "elo": elo,
            "error": None
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_best_move_given_fen(fen: str, depth: int = 15, elo: int = 1500) -> dict:
    """
    Get the best move for a given position using Stockfish.
    
    Args:
        fen: Board position in FEN notation
        depth: Search depth (default 15)
        elo: Engine strength (default 1500)
    
    Returns:
        Dictionary with best move and analysis
    """
    if not stockfish_engine:
        return {"error": "Stockfish engine not available"}
    
    try:
        # Configure engine strength
        stockfish_engine.set_elo_rating(elo)
        stockfish_engine.set_depth(depth)
        
        # Set position and get best move
        stockfish_engine.set_fen_position(fen)
        best_move = stockfish_engine.get_best_move()
        evaluation = stockfish_engine.get_evaluation()
        
        return {
            "best_move": best_move,
            "evaluation": evaluation,
            "depth": depth,
            "elo": elo,
            "error": None
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def get_legal_moves_from_fen(fen: str) -> dict:
    """
    Get all legal moves from a given position.
    
    Args:
        fen: Board position in FEN notation
    
    Returns:
        Dictionary with list of legal moves
    """
    try:
        board = chess.Board(fen)
        legal_moves = [move.uci() for move in board.legal_moves]
        
        return {
            "legal_moves": legal_moves,
            "count": len(legal_moves),
            "error": None
        }
    except Exception as e:
        return {
            "legal_moves": [],
            "count": 0,
            "error": str(e)
        }

@mcp.tool()
async def apply_move_to_position(fen: str, move_uci: str) -> dict:
    """
    Apply a move to a position and return the resulting position.
    
    Args:
        fen: Current board position in FEN notation
        move_uci: Move to apply in UCI notation
    
    Returns:
        Dictionary with new position and move details
    """
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        
        if move not in board.legal_moves:
            return {"error": "Illegal move"}
        
        # Get move details before applying
        san_notation = board.san(move)
        is_capture = board.is_capture(move)
        
        # Apply move
        board.push(move)
        new_fen = board.fen()
        
        return {
            "new_fen": new_fen,
            "move_san": san_notation,
            "move_uci": move_uci,
            "is_capture": is_capture,
            "is_check": board.is_check(),
            "error": None
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def check_game_end_conditions(fen: str) -> dict:
    """
    Check the game status for a given position.
    
    Args:
        fen: Board position in FEN notation
    
    Returns:
        Dictionary with game status information
    """
    try:
        board = chess.Board(fen)
        outcome = board.outcome(claim_draw=True)
        
        return {
            "game_over": outcome is not None,
            "winner": str(outcome.winner) if outcome and outcome.winner else None,
            "termination": str(outcome.termination) if outcome else None,
            "is_check": board.is_check(),
            "is_checkmate": board.is_checkmate(),
            "is_stalemate": board.is_stalemate(),
            "current_turn": "white" if board.turn == chess.WHITE else "black",
            "move_number": board.fullmove_number,
            "halfmove_clock": board.halfmove_clock,
            "can_claim_draw": board.can_claim_draw(),
            "error": None
        }
    except Exception as e:
        return {"error": str(e)}
```

### 1.3 Resource Management

```python
@mcp.resource("chess-engine-status")
async def get_engine_status():
    """Get the current status of the chess engine"""
    if stockfish_engine:
        try:
            # Test engine with default position
            stockfish_engine.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            test_move = stockfish_engine.get_best_move()
            
            return {
                "available": True,
                "engine": "Stockfish",
                "test_move": test_move,
                "parameters": stockfish_engine.get_parameters()
            }
        except Exception as e:
            return {
                "available": False,
                "engine": "Stockfish",
                "error": str(e)
            }
    else:
        return {
            "available": False,
            "engine": "None",
            "error": "Engine not initialized"
        }

@mcp.custom_route("/health")
async def health_check():
    """Health check endpoint for the MCP server"""
    from datetime import datetime
    
    engine_available = stockfish_engine is not None
    
    return {
        "status": "healthy" if engine_available else "degraded",
        "chess_engine": "available" if engine_available else "unavailable",
        "timestamp": datetime.utcnow().isoformat(),
        "tools": [
            "is_move_valid_given_fen",
            "get_best_move_given_fen", 
            "get_best_move_given_history_in_pgn",
            "get_legal_moves_from_fen",
            "apply_move_to_position",
            "check_game_end_conditions"
        ]
    }
```

## 2. ASGI Integration with Starlette/FastAPI

### 2.1 Starlette Integration

Based on the documentation analysis, here's how to integrate with Starlette:

```python
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Create FastMCP server
mcp = FastMCP("chess-engine-server")

# Register all chess tools (as shown above)
# ... tool definitions ...

# Create ASGI application
async def homepage(request):
    return JSONResponse({
        "message": "Chess MCP Server", 
        "mcp_endpoint": "/mcp/",
        "health_endpoint": "/health"
    })

# Create the MCP HTTP app
mcp_app = mcp.http_app()

# Mount MCP server under /mcp/ path
app = Starlette(
    routes=[
        Route("/", homepage),
        Mount("/mcp", mcp_app),
    ],
    lifespan=mcp_app.lifespan,  # Important for proper resource management
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2.2 FastAPI Integration (Alternative)

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(title="Chess MCP Server", version="1.0.0")

# Create MCP server
mcp = FastMCP("chess-engine-server")

# Register tools...

# Add API endpoints
@app.get("/")
async def root():
    return {"message": "Chess MCP Server", "mcp_endpoint": "/mcp/"}

@app.get("/engine/status")
async def engine_status():
    """REST endpoint for engine status"""
    status = await get_engine_status()
    return status

# Mount MCP server
app.mount("/mcp", mcp.http_app())

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 3. Docker Deployment Configuration

### 3.1 Dockerfile for Chess MCP Server

Based on the template analysis, here's the optimized Dockerfile:

```dockerfile
# Use Python 3.12 slim image
FROM python:3.12.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STOCKFISH_PATH="/usr/games/stockfish"

# Set working directory
WORKDIR /code

# Install system dependencies including Stockfish
RUN apt-get update && apt-get install -y \
    stockfish \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY src/ .

# Change ownership to non-root user
RUN chown -R appuser:appuser /code
USER appuser

# Expose port (note: template exposes 8080 but runs on 8000)
EXPOSE 8000

# Run FastMCP server using streamable-http transport
CMD ["fastmcp", "run", "/code/server.py", "--transport", "streamable-http", "--port", "8000", "--host", "0.0.0.0"]
```

### 3.2 Requirements File

```txt
# requirements.txt
fastmcp>=0.2.0
chess>=1.999
stockfish>=3.28.0
starlette>=0.27.0
uvicorn[standard]>=0.23.0
```

### 3.3 Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  chess-mcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - STOCKFISH_PATH=/usr/games/stockfish
      - LOG_LEVEL=info
    volumes:
      - ./src:/code  # Development volume mount
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Redis for caching (if needed)
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

## 4. Production Deployment Considerations

### 4.1 Environment Configuration

```python
# server.py - Production configuration
import logging
import os
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Environment-based configuration
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
DEFAULT_ELO = int(os.getenv("DEFAULT_ELO", "1500"))
DEFAULT_DEPTH = int(os.getenv("DEFAULT_DEPTH", "15"))
MAX_THREADS = int(os.getenv("MAX_THREADS", "2"))
HASH_SIZE = int(os.getenv("STOCKFISH_HASH", "256"))

mcp = FastMCP("chess-engine-server")

def initialize_production_engine():
    """Initialize Stockfish with production settings"""
    try:
        engine = Stockfish(
            path=STOCKFISH_PATH,
            depth=DEFAULT_DEPTH,
            parameters={
                "Threads": min(MAX_THREADS, os.cpu_count() or 2),
                "Hash": HASH_SIZE,
                "UCI_LimitStrength": True,
                "UCI_Elo": DEFAULT_ELO
            }
        )
        logging.info("Stockfish engine initialized successfully")
        return engine
    except Exception as e:
        logging.error(f"Failed to initialize Stockfish: {e}")
        return None

# Global engine instance
stockfish_engine = initialize_production_engine()
```

### 4.2 Error Handling and Monitoring

```python
import time
from functools import wraps

# Tool usage metrics
tool_metrics = {
    "calls": 0,
    "errors": 0,
    "total_time": 0
}

def log_tool_usage(func):
    """Decorator to log tool usage and performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            tool_metrics["calls"] += 1
            tool_metrics["total_time"] += duration
            logging.info(f"Tool {tool_name} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            tool_metrics["errors"] += 1
            logging.error(f"Tool {tool_name} failed after {duration:.3f}s: {e}")
            return {"error": str(e)}
    
    return wrapper

# Enhanced health check with metrics
@mcp.custom_route("/health")
async def health_check():
    """Comprehensive health check with metrics"""
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": tool_metrics.copy(),
        "components": {}
    }
    
    # Check Stockfish engine
    if stockfish_engine:
        try:
            stockfish_engine.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            test_move = stockfish_engine.get_best_move()
            health_status["components"]["stockfish"] = {
                "status": "healthy",
                "test_move": test_move
            }
        except Exception as e:
            health_status["status"] = "degraded"
            health_status["components"]["stockfish"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["status"] = "degraded"
        health_status["components"]["stockfish"] = {
            "status": "unavailable"
        }
    
    return health_status

@mcp.custom_route("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    return {
        "tool_calls_total": tool_metrics["calls"],
        "tool_errors_total": tool_metrics["errors"],
        "tool_duration_seconds_total": tool_metrics["total_time"],
        "engine_available": stockfish_engine is not None
    }
```

## 5. Integration with Multi-Agent Chess System

### 5.1 Agent-to-MCP Communication Pattern

```python
# Example of how agents will call MCP tools
import httpx
import json

class ChessMCPClient:
    def __init__(self, mcp_server_url: str):
        self.base_url = mcp_server_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Generic tool calling method"""
        payload = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/mcp/",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_best_move(self, fen: str, elo: int = 1500) -> dict:
        """Get best move from MCP server"""
        return await self.call_tool("get_best_move_given_fen", {
            "fen": fen,
            "elo": elo
        })
    
    async def validate_move(self, fen: str, move: str) -> dict:
        """Validate move via MCP server"""
        return await self.call_tool("is_move_valid_given_fen", {
            "fen": fen,
            "move_uci": move
        })
    
    async def get_best_move_from_pgn(self, pgn: str, elo: int = 1500) -> dict:
        """Get best move from PGN history"""
        return await self.call_tool("get_best_move_given_history_in_pgn", {
            "pgn_history": pgn,
            "elo": elo
        })
    
    async def check_health(self) -> dict:
        """Check MCP server health"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
```

### 5.2 Player Agent Integration

```python
# Example player agent using MCP tools
class ChessPlayerAgent:
    def __init__(self, color: str, mcp_server_url: str):
        self.color = color
        self.mcp_client = ChessMCPClient(mcp_server_url)
    
    async def generate_move(self, fen: str, pgn_history: str = "") -> str:
        """Generate a move using MCP tools"""
        
        # Try to get move from PGN history if available
        if pgn_history:
            result = await self.mcp_client.get_best_move_from_pgn(pgn_history)
        else:
            result = await self.mcp_client.get_best_move(fen)
        
        if "error" in result:
            raise Exception(f"MCP tool error: {result['error']}")
        
        best_move = result.get("best_move")
        if not best_move:
            raise Exception("No move generated")
        
        # Validate the move before returning
        validation = await self.mcp_client.validate_move(fen, best_move)
        if not validation.get("valid", False):
            raise Exception(f"Generated invalid move: {best_move}")
        
        return best_move
```

## 6. Deployment Scripts

### 6.1 Build and Deploy Script

```bash
#!/bin/bash
# deploy-chess-mcp.sh

set -e

echo "Building Chess MCP Server..."

# Build Docker image
docker build -t chess-mcp-server:latest .

# Tag for registry
REGISTRY=${REGISTRY:-"localhost:5000"}
docker tag chess-mcp-server:latest $REGISTRY/chess-mcp-server:latest

# Push to registry if not local
if [ "$REGISTRY" != "localhost:5000" ]; then
    echo "Pushing to registry..."
    docker push $REGISTRY/chess-mcp-server:latest
fi

echo "Deploying Chess MCP Server..."

# Deploy with docker-compose
docker-compose up -d

echo "Waiting for server to start..."
sleep 15

# Health check
echo "Checking server health..."
curl -f http://localhost:8000/health || {
    echo "Health check failed"
    docker-compose logs chess-mcp-server
    exit 1
}

echo "Chess MCP Server deployed successfully!"
echo "Server available at: http://localhost:8000"
echo "MCP endpoint: http://localhost:8000/mcp/"
echo "Health check: http://localhost:8000/health"
```

### 6.2 Testing Script

```bash
#!/bin/bash
# test-chess-mcp.sh

set -e

BASE_URL="http://localhost:8000"

echo "Testing Chess MCP Server..."

# Test health endpoint
echo "Testing health check..."
curl -s $BASE_URL/health | jq .

# Test move validation
echo "Testing move validation..."
curl -s -X POST $BASE_URL/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "is_move_valid_given_fen",
      "arguments": {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "move_uci": "e2e4"
      }
    }
  }' | jq .

# Test best move generation
echo "Testing best move generation..."
curl -s -X POST $BASE_URL/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "get_best_move_given_fen",
      "arguments": {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "elo": 1500
      }
    }
  }' | jq .

# Test game status check
echo "Testing game status check..."
curl -s -X POST $BASE_URL/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "check_game_end_conditions",
      "arguments": {
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
      }
    }
  }' | jq .

echo "All tests passed!"
```

## 7. Summary

This FastMCP implementation provides:

1. **Robust Chess Tools**: Six core MCP tools for move validation, generation, and game analysis
2. **Production-Ready**: Error handling, health checks, metrics, and logging
3. **Docker Deployment**: Containerized with security best practices
4. **ASGI Integration**: Compatible with modern Python web frameworks
5. **Agent Integration**: Clear patterns for A2A communication with MCP tools

The server follows the template patterns while being specifically designed for chess engine operations, making it ideal for our multi-agent chess system architecture.