"""
Chess Agent Definition using Google ADK and MCP integration.

Based on currency-agent agent.py pattern from Google ADK examples.
"""
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

# Chess agent system instructions
CHESS_AGENT_INSTRUCTION = """
You are a stateless chess playing agent specialized in position analysis and move generation.

Your capabilities:
1. Analyze chess positions provided in FEN notation
2. Generate optimal moves using Stockfish engine integration
3. Validate positions and moves for legality
4. Return moves in UCI notation (e.g., "e2e4", "g1f3", "e7e8q")

Process:
1. Use validate_fen to verify the input position
2. Use get_stockfish_move to get the best move recommendation
3. Use validate_move to confirm move legality
4. Return ONLY the UCI move string

Critical requirements:
- You are stateless - no memory between requests
- Always return moves in UCI format (source+destination, e.g., "e2e4")
- For pawn promotions, append piece type (e.g., "e7e8q" for queen promotion)
- If validation fails, explain the error clearly
- Never add commentary, reasoning, or explanation unless error occurred

Example interactions:
- Input: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
- Output: "e2e4"
"""

def create_chess_agent() -> LlmAgent:
    """
    Create the stateless chess playing agent with MCP server connection.
    
    Returns:
        LlmAgent configured for chess playing with Stockfish integration
    """
    # Get chess MCP server URL from environment
    chess_mcp_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
    
    # Create MCP toolset for chess server connection
    chess_toolset = MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=chess_mcp_url
        )
    )
    
    # Create and return the LLM agent
    return LlmAgent(
        model="gemini-2.5-flash",
        name="chess_player_agent",
        description="An agent that can help with chess move generation",
        instruction=CHESS_AGENT_INSTRUCTION,
        tools=[chess_toolset]
    )