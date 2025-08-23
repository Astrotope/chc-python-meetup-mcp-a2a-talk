"""
Chess MCP Server with Stockfish integration.

Provides chess tools via MCP protocol for move validation, execution, 
and engine analysis using Stockfish.
"""
import os
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
import chess
import chess.engine
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Load environment variables from component-specific .env file
load_dotenv("./.env")

# Environment configuration
STOCKFISH_PATH = os.getenv("STOCKFISH_PATH", "/usr/local/bin/stockfish")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "5000"))
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")

# Core business logic functions (not decorated, for testing)
def validate_move_logic(fen: str, move_uci: str) -> Dict[str, Any]:
    """Check if a move is valid given a board position."""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        is_legal = move in board.legal_moves
        return {
            "valid": is_legal,
            "error": None
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }

def make_move_logic(fen: str, move_uci: str) -> Dict[str, Any]:
    """Execute a move on the board and return new position."""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        
        if move in board.legal_moves:
            board.push(move)
            return {
                "success": True,
                "new_fen": board.fen(),
                "error": None
            }
        else:
            return {
                "success": False,
                "new_fen": fen,
                "error": "Invalid move"
            }
    except Exception as e:
        return {
            "success": False,
            "new_fen": fen,
            "error": str(e)
        }

def get_stockfish_move_logic(fen: str, time_limit: float = 2.0) -> Dict[str, Any]:
    """Get best move from Stockfish engine."""
    try:
        board = chess.Board(fen)
        
        with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
            result = engine.play(board, chess.engine.Limit(time=time_limit))
            
            return {
                "success": True,
                "move_uci": result.move.uci() if result.move else None,
                "error": None
            }
    except Exception as e:
        return {
            "success": False,
            "move_uci": None,
            "error": str(e)
        }

def get_game_status_logic(fen: str) -> Dict[str, Any]:
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
            "current_turn": "white" if board.turn else "black",
            "error": None
        }
    except Exception as e:
        return {
            "is_game_over": False,
            "winner": None,
            "termination": None,
            "is_check": False,
            "legal_moves_count": 0,
            "current_turn": "unknown",
            "error": str(e)
        }

def validate_fen_logic(fen: str) -> Dict[str, Any]:
    """Check if a FEN string is syntactically valid and represents a legal chess position."""
    try:
        board = chess.Board(fen)
        return {
            "valid": True,
            "error": None
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }

def get_legal_moves_logic(fen: str) -> Dict[str, Any]:
    """Get all legal moves for a position in UCI notation."""
    try:
        board = chess.Board(fen)
        legal_moves_uci = [move.uci() for move in board.legal_moves]
        
        return {
            "success": True,
            "legal_moves": legal_moves_uci,
            "count": len(legal_moves_uci),
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "legal_moves": [],
            "count": 0,
            "error": str(e)
        }

def health_check_logic() -> Dict[str, Any]:
    """Check server health and chess engine availability."""
    try:
        # Test basic chess functionality
        board = chess.Board()
        legal_moves = len(list(board.legal_moves))
        
        # Test Stockfish availability
        with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
            engine_info = str(engine.id)
        
        return {
            "status": "healthy",
            "chess_engine": "available",
            "engine_info": engine_info[:100],  # Limit length
            "legal_moves_test": legal_moves == 20,  # Standard starting position
            "stockfish_path": STOCKFISH_PATH,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "chess_engine": "unavailable",
            "error": str(e),
            "stockfish_path": STOCKFISH_PATH,
            "timestamp": datetime.utcnow().isoformat()
        }

# Create FastMCP server instance and register tools
mcp = FastMCP("chess-server")

@mcp.tool()
def validate_move(fen: str, move_uci: str) -> Dict[str, Any]:
    """Check if a move is valid given a board position."""
    return validate_move_logic(fen, move_uci)

@mcp.tool()
def make_move(fen: str, move_uci: str) -> Dict[str, Any]:
    """Execute a move on the board and return new position."""
    return make_move_logic(fen, move_uci)

@mcp.tool()
def get_stockfish_move(fen: str, time_limit: float = 2.0) -> Dict[str, Any]:
    """Get best move from Stockfish engine."""
    return get_stockfish_move_logic(fen, time_limit)

@mcp.tool()
def get_game_status(fen: str) -> Dict[str, Any]:
    """Check game status including checkmate, stalemate, and draw conditions."""
    return get_game_status_logic(fen)

@mcp.tool()
def validate_fen(fen: str) -> Dict[str, Any]:
    """Check if a FEN string is syntactically valid and represents a legal chess position."""
    return validate_fen_logic(fen)

@mcp.tool()
def get_legal_moves(fen: str) -> Dict[str, Any]:
    """Get all legal moves for a position in UCI notation."""
    return get_legal_moves_logic(fen)

@mcp.tool()
def health_check() -> Dict[str, Any]:
    """Check server health and chess engine availability."""
    return health_check_logic()

# Health check route for deployment platforms like sliplane.io
@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """HTTP health check endpoint for deployment platforms."""
    health_data = health_check_logic()
    
    # Return 200 if healthy, 503 if unhealthy
    status_code = 200 if health_data["status"] == "healthy" else 503
    
    return JSONResponse(
        content={
            "status": health_data["status"],
            "chess_engine": health_data["chess_engine"],
            "timestamp": health_data["timestamp"],
            "service": "chess-mcp-server"
        },
        status_code=status_code
    )

def start_chess_mcp_server():
    """Start the chess MCP server."""
    print(f"Starting chess MCP server at {datetime.now()}")
    print(f"Server: {MCP_SERVER_HOST}:{MCP_SERVER_PORT}")
    print(f"Stockfish path: {STOCKFISH_PATH}")
    
    # Test Stockfish availability on startup
    health = health_check_logic()
    if health["status"] == "healthy":
        print("✅ Stockfish engine is available")
    else:
        print(f"❌ Stockfish engine test failed: {health.get('error')}")
    
    # Start the MCP server with streamable HTTP transport
    mcp.run(transport="streamable-http", host=MCP_SERVER_HOST, port=MCP_SERVER_PORT)

if __name__ == "__main__":
    start_chess_mcp_server()
