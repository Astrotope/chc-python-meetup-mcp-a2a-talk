# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import warnings
import logging
from dotenv import load_dotenv
import warnings
import agentops

warnings.filterwarnings("ignore", message=".*\[EXPERIMENTAL\].*", category=UserWarning)

logger = logging.getLogger(__name__)
log_level = getattr(logging, os.getenv('ADK_LOG_LEVEL', 'WARNING').upper())
logging.basicConfig(level=log_level)

# Suppress INFO logging
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_adk").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google.adk").setLevel(logging.WARNING)
logging.getLogger("google.genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from google.adk import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from google.adk.planners import BuiltInPlanner
from google.genai import types

# Import our chess game management system
from chess_game_manager import (
    ChessGameManager,
    start_game,
    play_turn,
    apply_move,
    get_game_status,
    reset_game
)

# Load environment variables
load_dotenv()

# Initialize AgentOps for observability (if enabled)
if os.getenv("AGENTOPS_USE", "false").lower() == "true":
    agentops.init(
        api_key=os.getenv("AGENTOPS_API_KEY"),
        tags=["chess", "orchestrator", "adk", "a2a"]
    )
    print("🔍 AgentOps observability enabled for orchestrator agent")

# Legacy function - now handled by ChessGameManager
# Keeping for compatibility if needed
def make_move(fen: str, move_uci: str) -> str:
    """Legacy move function - use ChessGameManager.make_move() instead"""
    import chess
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    board.push(move)
    return board.fen()

# Configure remote player agents with environment variable support
white_player_url = os.getenv("WHITE_PLAYER_URL", "http://localhost:8005")
black_player_url = os.getenv("BLACK_PLAYER_URL", "http://localhost:8006")

print(f"🔗 WHITE_PLAYER_URL: {white_player_url}")
print(f"🔗 BLACK_PLAYER_URL: {black_player_url}")

white_player_agent = RemoteA2aAgent(
    name="white_player",
    agent_card=f"{white_player_url}/.well-known/agent-card.json",
    description="White chess player agent that generates moves for white pieces"
)

black_player_agent = RemoteA2aAgent(
    name="black_player",
    agent_card=f"{black_player_url}/.well-known/agent-card.json",
    description="Black chess player agent that generates moves for black pieces"
)

print(f"🔗 White agent card URL: {white_player_url}/.well-known/agent-card.json")
print(f"🔗 Black agent card URL: {black_player_url}/.well-known/agent-card.json")

# Create AgentTool wrappers for direct A2A player agent communication
white_agent_tool = AgentTool(agent=white_player_agent)
black_agent_tool = AgentTool(agent=black_player_agent)

print("🔧 AgentTools created for white and black players")

root_agent = Agent(
    model=os.getenv("ORCHESTRATOR_MODEL", "gemini-2.5-flash"),
    name="chess_orchestrator",
    description="Chess game orchestrator with multistep planning that manages complete chess games",
    instruction="""You are a Chess Game Orchestrator that plays COMPLETE AUTOMATED GAMES between AI agents.

AUTONOMOUS GAMEPLAY MODE:
When user says "start game" or "begin game", you must:
1. Use 'start_game' tool to initialize the game
2. IMMEDIATELY begin automated gameplay loop:
   - Use 'white_player' tool with FEN as input to get white's move
   - Use 'apply_move' with 'uci_move' parameter to execute white's move
   - Use 'black_player' tool with FEN as input to get black's move
   - Use 'apply_move' with 'uci_move' parameter to execute black's move
   - Repeat until game ends (checkmate/stalemate/draw)
3. Report final game result

AUTOMATED TURN SEQUENCE:
1. Use 'get_game_status' to get current FEN and turn information
2. If white's turn: Use 'white_player' tool with FEN as input
3. If black's turn: Use 'black_player' tool with FEN as input
4. Use 'apply_move' with 'uci_move' parameter to execute the returned move
5. Continue immediately to next turn
6. Stop only when game is over

AVAILABLE TOOLS:
- 'start_game': Initialize new chess game
- 'get_game_status': Get current game state and FEN
- 'white_player': Get UCI move from white player (pass FEN as input)
- 'black_player': Get UCI move from black player (pass FEN as input)
- 'apply_move': Execute UCI move (requires 'uci_move' parameter)
- 'reset_game': Reset to starting position

PLANNING APPROACH:
- Plan complete automated games from start to finish
- Never ask user for moves - use player agent tools
- Handle invalid moves by requesting new ones from the same player
- Continue playing until natural game end

DO NOT ask users for moves. DO NOT wait for input. Play complete games automatically.

Example flow: 'start_game' → 'get_game_status' → 'white_player'(fen="...") → 'apply_move'(uci_move="e2e4") → 'black_player'(fen="...") → 'apply_move'(uci_move="e7e5") → repeat until game ends.""",

    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=int(os.getenv("ORCHESTRATOR_THINKING_BUDGET", "4096"))
        )
    ),

    tools=[
        FunctionTool(start_game),
        FunctionTool(play_turn),
        FunctionTool(apply_move),
        FunctionTool(get_game_status),
        FunctionTool(reset_game),
        white_agent_tool,
        black_agent_tool
    ],
    generate_content_config=types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=int(os.getenv("ORCHESTRATOR_MAX_CALLS", "15"))
        ),
        safety_settings=[
            types.SafetySetting(  # avoid false alarm about rolling dice.
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ]
    ),
)

from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Make your agent A2A-compatible
a2a_app = to_a2a(root_agent, port=8007)
