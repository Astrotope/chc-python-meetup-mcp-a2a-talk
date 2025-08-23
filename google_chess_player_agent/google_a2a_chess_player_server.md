# Google A2A Chess Player Agent - Technical Design & Implementation Plan

## Project Overview

This document outlines the design and implementation plan for a Google A2A (Agent-to-Agent) chess player agent using Google's ADK (Agent Development Kit) and A2A Python SDK. The agent will replicate the functionality of the existing pydantic.ai chess player agent but using Google's A2A framework for standardized agent communication.

## Architecture Overview

### Core Components

1. **a2a_chess_player_agent_server.py** - Main server application (FastAPI + A2A)
2. **a2a_chess_player_agent.py** - Agent implementation with chess logic
3. **a2a_chess_player_agent_executor.py** - Custom executor for A2A request handling
4. **a2a_chess_player_agent_test_client.py** - Single-turn test client

### Reference Implementation Analysis

Based on the currency-agent example, Google ADK documentation, and codelabs, our implementation follows these patterns:

#### Server Architecture (`__main__.py` pattern)
```python
# Key imports
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler

# Configuration patterns
- Environment variable validation (GOOGLE_API_KEY)
- Agent skill and card definitions
- FastAPI-based A2A server with uvicorn
- In-memory services (artifact, memory, session)
```

#### Agent Implementation (`agent.py` pattern)
```python
# Key components
- LlmAgent with gemini-2.0-flash model
- MCPToolset for chess MCP server integration
- Specialized system instructions for chess
- StreamableHTTPConnectionParams for tool connection
```

#### Executor Pattern (`agent_executor.py` pattern)
```python
# Key functionality from codelab #6
- Custom AgentExecutor inheritance
- Async execute() method for request processing
- A2A ↔ Google GenAI part conversion
- Event processing (final responses, intermediate updates)
- Session management and task status tracking
```

## A2A Protocol Integration Insights

### From Codelab Analysis

**A2A Protocol Purpose** (Codelab #7):
- Enables "seamless communication and collaboration between AI agents"
- Allows agents to discover, communicate, and collaborate across frameworks
- Model-agnostic approach supporting interoperability

**Core A2A Components**:
1. **AgentSkill**: Defines agent capabilities and example interactions
2. **AgentCard**: Provides agent connection/discovery metadata
3. **AgentExecutor**: Handles core request processing logic

**Request Processing Flow** (Codelab #6):
1. Immediately notify task submission
2. Run agent through async generator
3. Handle different event types:
   - Final responses
   - Intermediate status updates
   - Function call events
4. Convert between A2A and GenAI message formats

## Technical Specifications

### Dependencies

**Core A2A & ADK Dependencies:**
```bash
uv add a2a-sdk
uv add google-adk
```

**Chess Integration:**
```bash
uv add python-chess
uv add python-dotenv
```

### Agent Configuration

#### AgentSkill Definition
```python
skill = AgentSkill(
    id="chess-move-generator",
    name="Chess Move Generator",
    description="Generates optimal chess moves using Stockfish engine via MCP",
    tags=["chess", "strategy", "stockfish", "uci"],
    example_interactions=[
        "Generate best move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "What's the best move in this position: r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 1"
    ]
)
```

#### AgentCard Definition (from Codelab #7)
```python
agent_card = AgentCard(
    name="Chess Player Agent",
    description="Stateless chess agent that analyzes positions and returns optimal moves in UCI notation",
    url=f"http://{host}:{port}/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=False)
)
```

### Chess MCP Integration

#### Tool Configuration
```python
# Connect to existing chess MCP server
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

chess_mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
    )
)
```

#### Available MCP Tools
From the existing chess MCP server:
- `validate_fen` - Validate FEN position strings
- `validate_move` - Check move legality
- `make_move` - Execute moves on board
- `get_stockfish_move` - Get engine recommendations
- `get_game_status` - Check game state
- `get_legal_moves` - List all legal moves
- `health_check` - Server health verification

### Agent Instructions

#### System Prompt
```python
instruction = """
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
```

## Implementation Details

### File Structure
```
google_chess_player_agent/
├── a2a_chess_player_agent_server.py    # Main server (FastAPI + A2A)
├── a2a_chess_player_agent.py           # Agent definition & MCP integration
├── a2a_chess_player_agent_executor.py  # Custom A2A executor
├── a2a_chess_player_agent_test_client.py # Test client
├── .env                                 # Environment configuration
├── pyproject.toml                       # Dependencies
└── README.md                           # Setup instructions
```

### Key Implementation Patterns

#### 1. Server Setup (a2a_chess_player_agent_server.py)
```python
# Based on currency-agent __main__.py pattern + codelab insights
import click
from google.adk.runners import Runner
from google.adk.services import InMemoryArtifactService, InMemoryMemoryService, InMemorySessionService
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from .agent import create_chess_agent
from .agent_executor import ChessAgentExecutor

@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10000)
def main(host: str, port: int):
    # Validate environment (GOOGLE_API_KEY)
    # Create agent and ADK services
    # Setup AgentCard with connection metadata
    # Create A2AFastAPIApplication with ChessAgentExecutor
    # Launch uvicorn server
```

#### 2. Agent Definition (a2a_chess_player_agent.py)
```python
# Based on currency-agent agent.py pattern
from google.adk.agents import LlmAgent
from mcp.toolsets import MCPToolset  # For chess MCP integration

def create_chess_agent() -> LlmAgent:
    chess_toolset = MCPToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        )
    )

    return LlmAgent(
        name="chess_player_agent",
        model="gemini-2.0-flash",
        instruction=CHESS_AGENT_INSTRUCTION,
        toolsets=[chess_toolset]
    )
```

#### 3. Custom Executor (a2a_chess_player_agent_executor.py)
```python
# Based on currency-agent executor + codelab #6 patterns
from a2a.server.request_handlers import AgentExecutor
from google.adk.runners import Runner

class ChessAgentExecutor(AgentExecutor):
    def __init__(self, runner: Runner):
        self.runner = runner

    async def execute(self, request: AgentRequest) -> AgentResponse:
        # Step 1: Immediately notify task submission
        await self.task_updater.submit_task(request.task_id)

        # Step 2: Convert A2A request to ADK format
        genai_parts = convert_a2a_parts_to_genai(request.message.parts)

        # Step 3: Run agent through async generator
        async for event in self._run_agent(genai_parts):
            await self._process_request(event, request.task_id)

        # Step 4: Return final response in A2A format
        return self._build_a2a_response(final_result)

    async def _run_agent(self, genai_parts):
        # Execute chess agent with MCP tool integration
        pass

    async def _process_request(self, event, task_id):
        # Handle different event types:
        # - Final responses (chess moves)
        # - Intermediate updates (tool calls)
        # - Function call events (MCP interactions)
        pass
```

#### 4. Test Client (a2a_chess_player_agent_test_client.py)
```python
# Based on currency-agent test_client.py pattern
from a2a.client import A2AClient
from a2a.model import SendMessageRequest, MessageSendParams

async def test_chess_move_generation():
    client = A2AClient(base_url="http://localhost:10000")

    # Test standard opening position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    payload = create_send_message_payload(
        text=f"Generate best move for FEN: {fen}",
        role="user"
    )

    response = await client.send_message(
        SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
    )

    print(f"Chess move: {response.result}")
```

### Environment Configuration

#### Required Environment Variables
```bash
# Google AI Studio Authentication (required)
GOOGLE_API_KEY=<your_api_key_here>
GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Chess MCP Server Integration (same as original agent)
CHESS_MCP_SERVER_URL=http://localhost:5000/mcp

# A2A Server Configuration
A2A_SERVER_HOST=localhost
A2A_SERVER_PORT=10000

# Agent Configuration
AGENT_NAME=chess-player-agent
AGENT_VERSION=1.0.0
```

#### Setup Environment
```bash
echo "GOOGLE_API_KEY=<your_api_key_here>" >> .env \
&& echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> .env
```

## Integration with Existing Chess MCP Server

### MCP Server Connection
The agent will connect to the existing chess MCP server at `http://localhost:5000/mcp` using the ADK's MCPToolset functionality. This maintains compatibility with the current chess infrastructure while adding A2A protocol support.

### Tool Mapping
```python
# MCP tools → Agent capabilities
mcp_tools = [
    "validate_fen",      # → Position validation
    "get_stockfish_move", # → Move generation
    "validate_move",     # → Move validation
    "get_game_status",   # → Game state analysis
    "get_legal_moves",   # → Legal move enumeration
    "make_move",         # → Position updates (if needed)
    "health_check"       # → Health monitoring
]
```

## A2A Protocol Communication Flow

### Request Processing (Based on Codelab #6)
```
1. A2A Client → SendMessageRequest → Chess Agent Server
2. ChessAgentExecutor.execute() → Task submission notification
3. Convert A2A parts → GenAI parts → ADK Agent
4. Agent → MCP Tools → Chess MCP Server → Stockfish
5. Process events: tool calls, intermediate updates, final response
6. Convert GenAI response → A2A format → Client
```

### Message Format Examples
```python
# Input message (A2A format)
{
    "role": "user",
    "parts": [{"text": "Generate best move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}]
}

# Output message (A2A format)
{
    "role": "assistant",
    "parts": [{"text": "e2e4"}]
}
```

## Testing Strategy

### Unit Tests
- Agent initialization and configuration
- MCP toolset integration
- FEN validation and move generation
- Error handling for invalid positions

### Integration Tests
- End-to-end A2A communication
- Chess MCP server connectivity
- Multi-turn conversation handling
- Performance and latency testing

### Test Scenarios
```python
test_cases = [
    {
        "name": "Standard Opening",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "expected_moves": ["e2e4", "d2d4", "g1f3", "b1c3"]  # Common openings
    },
    {
        "name": "Tactical Position",
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 1",
        "expected_type": "tactical_move"
    },
    {
        "name": "Endgame Position",
        "fen": "8/8/8/8/8/8/8/K1k5 w - - 0 1",
        "expected_result": "stalemate_or_draw"
    }
]
```

## Deployment Considerations

### Local Development
```bash
# Start chess MCP server
cd ../chess-mcp-server
uv run python chess_mcp_server.py

# Start A2A chess agent
cd ../google_chess_player_agent
uv run python a2a_chess_player_agent_server.py --host localhost --port 10000
```

### Local Deployment
- Health check endpoints for monitoring

## Health Checks
- A2A server health endpoint
- Chess MCP server connectivity
- Google AI Studio service status
- Agent readiness indicators

## Success Criteria

### Functional Requirements
1. ✅ Generates valid chess moves in UCI notation
2. ✅ Validates FEN positions correctly
3. ✅ Integrates with existing chess MCP server
4. ✅ Supports A2A protocol communication
5. ✅ Maintains stateless operation


### Integration Requirements
1. ✅ Compatible with existing chess MCP infrastructure
2. ✅ Supports standard A2A protocol features
4. ✅ Extensible for additional chess variants
5. ✅ Cross-framework agent interoperability

This implementation plan provides a comprehensive roadmap for building a production-ready Google A2A chess player agent that maintains compatibility with existing chess infrastructure while leveraging Google's agent development ecosystem and A2A protocol for cross-framework interoperability.
