"""
Chess Player Agent using pydantic.ai with MCP integration.

Stateless agent that takes FEN input and returns best move in UCI notation.
"""
import os
from typing import Dict, Any
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

# Load environment variables from component-specific .env file
load_dotenv("./.env")

# Environment configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHESS_MCP_SERVER_URL = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
AGENT_MODEL = os.getenv("AGENT_MODEL", "openai:gpt-4o")
AGENT_NAME = os.getenv("AGENT_NAME", "chess-player-agent")
AGENT_PORT = int(os.getenv("AGENT_PORT", "5001"))
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0")

# Structured response model for UCI move extraction
class MoveResponse(BaseModel):
    move_uci: str

def create_chess_agent():
    """Create the stateless chess playing agent with MCP server connection."""
    # Connect to chess MCP server
    chess_mcp_server = MCPServerStreamableHTTP(url=CHESS_MCP_SERVER_URL)

    # Create the chess playing agent
    return Agent(
        model=AGENT_MODEL,
        instructions="""
        You are a stateless chess playing agent. For each FEN position input:

        1. Use validate_fen to check if the FEN is valid
        2. Use get_stockfish_move to get the best move in UCI format
        3. Use validate_move to confirm the move is legal
        4. Return ONLY the UCI move string (e.g., "e2e4", "g1f3", "e7e8q")

        CRITICAL:
        - You are stateless - no memory between requests
        - Return only the raw UCI move string
        - If validation fails, explain the error clearly
        - Never add reasoning, commentary, or explanation
        """,
        toolsets=[chess_mcp_server],
        output_type=MoveResponse,
    )

async def generate_move(fen: str) -> str:
    """
    Generate best move for given FEN position.

    Args:
        fen: Chess position in FEN notation

    Returns:
        UCI move string (e.g., "e2e4") or raises exception on error
    """
    agent = create_chess_agent()

    async with agent:
        result = await agent.run(f"Generate the best move for FEN: {fen}")

    # Extract UCI move from structured response
    return result.output.move_uci

async def health_check(request):
    """Health check endpoint that tests MCP server connectivity."""
    try:
        # Test MCP server connectivity by creating agent
        agent = create_chess_agent()

        # Test with a simple FEN validation (doesn't require Stockfish)
        test_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        async with agent:
            # Try to validate a basic FEN to test MCP connectivity
            result = await agent.run(f"Use validate_fen to check if this FEN is valid: {test_fen}")

        return JSONResponse({
            "status": "healthy",
            "mcp_server": "available",
            "mcp_server_url": CHESS_MCP_SERVER_URL,
            "agent_name": AGENT_NAME,
            "model": AGENT_MODEL
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "mcp_server": "unavailable",
            "error": str(e),
            "mcp_server_url": CHESS_MCP_SERVER_URL
        }, status_code=503)

def create_app():
    """Create the main Starlette application with health and A2A endpoints."""
    # Test: Return just the A2A app as suggested
    agent = create_chess_agent()
    app = agent.to_a2a()
    
    return app
    
    # Commented out the complex mounting logic to test theory
    # try:
    #     # Try to import FastA2A components for proper initialization
    #     from fasta2a import FastA2A, InMemoryStorage, InMemoryBroker, InMemoryWorker
    #     
    #     # Create A2A components according to FastA2A documentation
    #     storage = InMemoryStorage()
    #     broker = InMemoryBroker()
    #     worker = InMemoryWorker(storage=storage, broker=broker)
    #     
    #     @asynccontextmanager
    #     async def lifespan(app: FastA2A):
    #         async with app.task_manager:
    #             async with worker.run():
    #                 yield
    #     
    #     # Create agent and A2A app with proper configuration
    #     agent = create_chess_agent()
    #     a2a_app = agent.to_a2a(storage=storage, broker=broker, lifespan=lifespan)
    #     
    #     # Main app lifespan to handle A2A lifespan
    #     @asynccontextmanager
    #     async def main_lifespan(app):
    #         # Start A2A app lifespan
    #         async with a2a_app.router.lifespan_context(a2a_app):
    #             yield
    #     
    #     # Create main app with both health and A2A routes
    #     app = Starlette(
    #         routes=[
    #             Route("/health", health_check),
    #             Mount("/", a2a_app)
    #         ],
    #         lifespan=main_lifespan
    #     )
    #     
    # except ImportError:
    #     # Fallback to simple agent.to_a2a() if FastA2A components not available
    #     agent = create_chess_agent()
    #     a2a_app = agent.to_a2a()
    #     
    #     # Create main app without lifespan
    #     app = Starlette(routes=[
    #         Route("/health", health_check),
    #         Mount("/", a2a_app)
    #     ])

    # return app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    print(f"Starting {AGENT_NAME} on {AGENT_HOST}:{AGENT_PORT}")
    print(f"Chess MCP Server: {CHESS_MCP_SERVER_URL}")
    print(f"Using model: {AGENT_MODEL}")
    print(f"Health endpoint: http://{AGENT_HOST}:{AGENT_PORT}/health")
    print(f"A2A endpoint: http://{AGENT_HOST}:{AGENT_PORT}/")

    # Create and run the application
    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT)
