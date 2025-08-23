#!/usr/bin/env python3
"""
A2A Chess Player Agent Server

Main server application using Google ADK and A2A protocol.
Based on currency-agent __main__.py pattern from Google ADK examples.
"""
import os
import logging
import warnings
import click
from dotenv import load_dotenv
from google.adk.runners import Runner, InMemoryArtifactService, InMemoryMemoryService, InMemorySessionService
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from agent import create_chess_agent
from agent_executor import ChessAgentExecutor

# Load environment variables (for local development only)
if os.path.exists(".env"):
    load_dotenv(".env")

# Configure logging immediately
def configure_logging():
    """Configure logging levels to reduce debug output."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Set root logging level
    logging.getLogger().setLevel(getattr(logging, log_level, logging.INFO))
    
    # Suppress specific debug loggers
    debug_loggers = [
        "a2a.server.tasks.inmemory_task_store",
        "a2a.utils.telemetry", 
        "a2a.server.events.event_queue",
        "a2a.server.events.event_consumer",
        "a2a.server.tasks.task_manager",
        "a2a.server.apps.jsonrpc.jsonrpc_app",
        "mcp.client.streamable_http",
        "httpcore.connection",
        "httpcore.http11",
        "asyncio",
        "agent_executor",
        "google_adk.google.adk.tools.base_authenticated_tool",
        "google_genai.types"
    ]
    
    # Set debug loggers to ERROR level to suppress warnings
    target_level = logging.ERROR if log_level in ["WARNING", "ERROR", "CRITICAL"] else logging.INFO
    for logger_name in debug_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(target_level)
        logger.propagate = False  # Prevent propagation to root logger
    
    # Suppress specific Python warnings when in WARNING mode
    if log_level in ["WARNING", "ERROR", "CRITICAL"]:
        warnings.filterwarnings("ignore", category=UserWarning, message=".*EXPERIMENTAL.*BaseAuthenticatedTool.*")
        warnings.filterwarnings("ignore", category=UserWarning, module="google.adk.tools.mcp_tool.mcp_tool")
        warnings.filterwarnings("ignore", message=".*auth_config.*missing.*")
        warnings.filterwarnings("ignore", message=".*non-text parts in the response.*")

# Configure logging early
configure_logging()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
CHESS_MCP_SERVER_URL = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")

def validate_environment():
    """Validate required environment variables."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    print(f"✓ Google API Key configured")
    print(f"✓ Chess MCP Server: {CHESS_MCP_SERVER_URL}")
    print(f"✓ Using Vertex AI: {GOOGLE_GENAI_USE_VERTEXAI}")

def create_agent_skill() -> AgentSkill:
    """Create AgentSkill definition for chess move generation."""
    return AgentSkill(
        id="chess-move-generator",
        name="Chess Move Generator",
        description="Generates optimal chess moves using Stockfish engine via MCP",
        tags=["chess", "strategy", "stockfish", "uci"],
        example_interactions=[
            "Generate best move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "What's the best move in this position: r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 1"
        ]
    )

def create_agent_card(host: str, port: int) -> AgentCard:
    """Create AgentCard for A2A discovery and connection metadata."""
    skill = create_agent_skill()
    return AgentCard(
        name="Chess Player Agent",
        description="Stateless chess agent that analyzes positions and returns optimal moves in UCI notation",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill]
    )

@click.command()
@click.option("--host", default=None, help="Host to bind server to")
@click.option("--port", default=None, type=int, help="Port to bind server to")
def main(host: str, port: int):
    """Start the A2A Chess Player Agent server."""
    # Use environment variables with fallbacks for Sliplane compatibility
    if host is None:
        host = os.getenv("A2A_SERVER_HOST", os.getenv("HOST", "0.0.0.0"))
    if port is None:
        port = int(os.getenv("PORT", os.getenv("A2A_SERVER_PORT", "10000")))
    
    print("🚀 Starting A2A Chess Player Agent Server")
    print("=" * 50)
    
    # Validate environment
    validate_environment()
    
    # Create ADK services (in-memory for simplicity)
    print("📦 Initializing ADK services...")
    artifact_service = InMemoryArtifactService()
    memory_service = InMemoryMemoryService()
    session_service = InMemorySessionService()
    
    # Create chess agent
    print("♟️  Creating chess agent...")
    chess_agent = create_chess_agent()
    
    # Create ADK runner
    runner = Runner(
        app_name="Chess Player Agent",
        agent=chess_agent,
        artifact_service=artifact_service,
        memory_service=memory_service,
        session_service=session_service
    )
    
    # Create A2A components
    print("🤖 Setting up A2A components...")
    agent_card = create_agent_card(host, port)
    
    # Create custom executor
    chess_executor = ChessAgentExecutor(runner=runner, card=agent_card)
    
    # Create A2A FastAPI application
    print("🌐 Creating A2A FastAPI application...")
    request_handler = DefaultRequestHandler(
        agent_executor=chess_executor,
        task_store=InMemoryTaskStore()
    )
    app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    
    print("=" * 50)
    print(f"✅ Server ready!")
    print(f"📍 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🌍 URL: http://{host}:{port}/")
    print(f"🔍 Agent Card: http://{host}:{port}/.well-known/agent-card.json")
    print(f"♟️  Chess MCP: {CHESS_MCP_SERVER_URL}")
    print("=" * 50)
    
    # Start uvicorn server
    import uvicorn
    uvicorn.run(app.build(), host=host, port=port)

if __name__ == "__main__":
    main()