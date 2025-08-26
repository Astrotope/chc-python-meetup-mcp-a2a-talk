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
import agentops

from google.adk import Agent
#from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import BaseModel, Field

#from google.adk.agents import LlmAgent
from google.adk.tools import MCPToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams
from google.adk.planners import BuiltInPlanner
import warnings

warnings.filterwarnings("ignore", message=".*\[EXPERIMENTAL\].*", category=UserWarning)

# Load environment variables
load_dotenv()

# Initialize AgentOps for observability (if enabled)
if os.getenv("AGENTOPS_USE", "false").lower() == "true":
    agentops.init(
        api_key=os.getenv("AGENTOPS_API_KEY"),
        tags=["chess", "black-player", "adk", "a2a"]
    )
    print("🔍 AgentOps observability enabled for black player agent")

logger = logging.getLogger(__name__)
log_level = getattr(logging, os.getenv('ADK_LOG_LEVEL', 'WARNING').upper())
logging.basicConfig(level=log_level)

# Suppress INFO logging
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_adk").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google_adk.google.adk.tools.base_authenticated_tool").setLevel(logging.ERROR)
logging.getLogger("google_adk.google.adk.models.google_llm").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Configure MCP toolset for chess
mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=os.getenv("MCP_SERVER_URL", "http://localhost:8010/mcp")
    ),
    tool_filter=["validate_fen", "get_stockfish_move", "validate_move", "get_game_status", "get_legal_moves"]
)

# Store reference for cleanup
mcp_toolset._cleanup_method = mcp_toolset.close

# Define structured output schema for chess moves
class ChessMoveOutput(BaseModel):
    move: str = Field(description="UCI chess move notation like 'e7e5'",
                     pattern=r'^[a-h][1-8][a-h][1-8][qrbn]?$')


root_agent = Agent(
    model=os.getenv("BLACK_PLAYER_MODEL", "gemini-2.5-flash"),
    name="black_chess_player_agent",
    description="Black chess player that generates optimal moves for black pieces using chess MCP tools",
    instruction="""You generate chess moves for BLACK pieces only.

Process:
1. Use validate_fen to check if the provided FEN is valid
2. If FEN is invalid, use set_model_response tool with {"move": "Invalid FEN"}
3. If FEN is valid, use get_stockfish_move with the FEN to generate a UCI move
4. Use validate_move to verify the generated move is valid
5. Use set_model_response tool to return the final JSON: {"move": "e7e5"}

CRITICAL: Always use set_model_response as your final step with proper JSON format.
Example: set_model_response({"move": "e7e5"})""",
    tools=[mcp_toolset],
    output_schema=ChessMoveOutput,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=int(os.getenv("PLAYER_THINKING_BUDGET", "2048"))
        )
    ),
    generate_content_config=types.GenerateContentConfig(
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=int(os.getenv("PLAYER_MAX_CALLS", "15"))
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
a2a_app = to_a2a(root_agent, port=8006, host=os.getenv("BLACK_PLAYER_HOST", "host.docker.internal"))
