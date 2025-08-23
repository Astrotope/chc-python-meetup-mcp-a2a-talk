# A2A Protocol Implementation Notes

## Overview

Agent-to-Agent (A2A) Protocol is an open standard by Google Cloud that enables seamless communication between AI agents regardless of frameworks or vendors. This document summarizes key implementation patterns from "The Ultimate A2A Handbook" for our multi-agent chess system.

## Core A2A Concepts

### 1. AgentCard
Standardized JSON document describing an agent's identity and capabilities, hosted at `/.well-known/agent.json`:

```json
{
  "schema_version": "1.0.0",
  "name": "Chess Player Agent",
  "description": "AI agent that plays chess using Stockfish engine",
  "contact_email": "admin@example.com",
  "capabilities": ["a2a.text-chat"],
  "versions": [
    {
      "version": "1.0.0",
      "endpoint": "http://localhost:8001/a2a",
      "supports_streaming": true,
      "auth": {
        "type": "none"
      }
    }
  ]
}
```

### 2. Core Components
- **Task**: Stateful collaboration tracking progress toward a specific goal
- **Artifact**: Final immutable result produced by an agent
- **Message**: Exchange non-artifact content between agents
- **Part**: Smallest unit of content within messages/artifacts
- **Transport**: Communication mechanism (HTTP/HTTPS, gRPC, MQTT)

### 3. A2A vs MCP
- **A2A**: Inter-agent collaboration and communication
- **MCP**: Tool/API access for individual agents
- **Complementary**: A2A agents can be exposed as MCP tools

## Implementation Approaches

### 1. FastAPI from Scratch

Basic echo agent implementation:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uuid
import json
from datetime import datetime

app = FastAPI()

@app.get("/.well-known/agent.json")
async def get_agent_card():
    with open("agent.json") as f:
        return json.load(f)

@app.post("/a2a/tasks/send")
async def tasks_send(request: Request):
    data = await request.json()
    task_id = data.get("task_id", str(uuid.uuid4()))
    user_message = next((m for m in data.get("messages", []) 
                        if m.get("role") == "user"), None)
    
    if not user_message:
        return JSONResponse(status_code=400, content={"error": "No user message found"})

    parts = user_message.get("parts", [])
    text_parts = [p.get("text") for p in parts if p.get("type") == "text"]
    echo_text = f"Echo: {' '.join(text_parts)}"
    
    return {
        "task_id": task_id,
        "status": "completed",
        "created_time": datetime.utcnow().isoformat(),
        "updated_time": datetime.utcnow().isoformat(),
        "messages": [
            {
                "role": "agent",
                "parts": [{"type": "text", "text": echo_text}]
            }
        ]
    }

# Client usage
import requests

class SimpleA2AClient:
    def __init__(self, server_url):
        self.server_url = server_url
        
    def discover_agent(self):
        response = requests.get(f"{self.server_url}/.well-known/agent.json")
        return response.json()
        
    def send_message(self, text):
        payload = {
            "task_id": str(uuid.uuid4()),
            "messages": [
                {
                    "role": "user",
                    "parts": [{"type": "text", "text": text}]
                }
            ]
        }
        response = requests.post(f"{self.server_url}/a2a/tasks/send", json=payload)
        return response.json()
```

### 2. Google A2A SDK

Advanced implementation with Google's official SDK:

```python
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message

class ChessPlayerAgentExecutor(AgentExecutor):
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Extract move request from context
        fen = context.get_parameter("fen")
        
        # Get best move from MCP server
        result = await self.mcp_client.get_best_move(fen)
        best_move = result.get("best_move", "No move available")
        
        # Send response
        await event_queue.enqueue_event(new_agent_text_message(best_move))

# Agent configuration
skill = AgentSkill(
    id='generate_chess_move',
    name='Generate Chess Move',
    description='Generate the best chess move for a given position',
    tags=['chess', 'move', 'strategy'],
    examples=['Generate move for position: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'],
)

agent_card = AgentCard(
    name='Chess Player Agent',
    description='AI chess player using Stockfish engine',
    url='http://localhost:8001/',
    version='1.0.0',
    default_input_modes=['text'],
    default_output_modes=['text'],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

# Server setup
request_handler = DefaultRequestHandler(
    agent_executor=ChessPlayerAgentExecutor(mcp_client),
    task_store=InMemoryTaskStore(),
)

server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
)

uvicorn.run(server.build(), host='0.0.0.0', port=8001)
```

### 3. Python-A2A Library (Recommended)

Simplified implementation using python-a2a library:

```python
from python_a2a import A2AServer, skill, agent, run_server, TaskStatus, TaskState
import asyncio

@agent(
    name="Chess Player Agent",
    description="AI chess player using Stockfish engine",
    version="1.0.0"
)
class ChessPlayerAgent(A2AServer):

    def __init__(self, mcp_client, color="white"):
        super().__init__()
        self.mcp_client = mcp_client
        self.color = color

    @skill(
        name="Generate Move",
        description="Generate the best chess move for a given position",
        tags=["chess", "move", "strategy"],
        examples=["Generate move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"]
    )
    async def generate_move(self, fen, pgn_history=""):
        """Generate chess move using MCP tools"""
        try:
            if pgn_history:
                result = await self.mcp_client.get_best_move_from_pgn(pgn_history)
            else:
                result = await self.mcp_client.get_best_move(fen)
            
            if "error" in result:
                return f"Error generating move: {result['error']}"
            
            best_move = result.get("best_move")
            evaluation = result.get("evaluation", {})
            
            return f"Best move: {best_move} (Evaluation: {evaluation})"
            
        except Exception as e:
            return f"Error: {str(e)}"

    @skill(
        name="Validate Move",
        description="Validate if a chess move is legal",
        tags=["chess", "validation"],
        examples=["Validate move e2e4 for starting position"]
    )
    async def validate_move(self, fen, move):
        """Validate move using MCP tools"""
        try:
            result = await self.mcp_client.validate_move(fen, move)
            is_valid = result.get("valid", False)
            
            if is_valid:
                return f"Move {move} is valid"
            else:
                error = result.get("error", "Unknown validation error")
                return f"Move {move} is invalid: {error}"
                
        except Exception as e:
            return f"Validation error: {str(e)}"

    def handle_task(self, task):
        """Handle incoming A2A tasks"""
        message_data = task.message or {}
        content = message_data.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""
        
        try:
            # Parse chess-related requests
            if "generate move" in text.lower():
                # Extract FEN from message
                if "fen:" in text.lower():
                    fen = text.split("fen:")[1].strip().split()[0:6]  # Get FEN components
                    fen = " ".join(fen)
                else:
                    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Default
                
                # Generate move
                result = asyncio.run(self.generate_move(fen))
                
            elif "validate move" in text.lower():
                # Extract FEN and move from message
                # Implementation for move validation
                result = "Move validation not implemented in this example"
                
            else:
                result = f"I'm a {self.color} chess player. Ask me to 'generate move' or 'validate move'."
            
            task.artifacts = [{
                "parts": [{"type": "text", "text": result}]
            }]
            task.status = TaskStatus(state=TaskState.COMPLETED)
            
        except Exception as e:
            task.artifacts = [{
                "parts": [{"type": "text", "text": f"Error: {str(e)}"}]
            }]
            task.status = TaskStatus(state=TaskState.FAILED)
        
        return task

# Agent network for multi-agent coordination
class ChessAgentNetwork:
    def __init__(self):
        self.network = AgentNetwork(name="Chess Game Network")
        self.network.add("white_player", "http://localhost:8001")
        self.network.add("black_player", "http://localhost:8002")
        self.network.add("orchestrator", "http://localhost:8000")
    
    async def coordinate_game(self, session_id: str):
        """Coordinate a chess game between agents"""
        orchestrator = self.network.get_agent("orchestrator")
        
        # Start game
        response = orchestrator.ask(f"Start new game for session {session_id}")
        return response

# Usage
if __name__ == "__main__":
    from mcp_client import ChessMCPClient  # Our MCP client
    
    mcp_client = ChessMCPClient("http://localhost:8003")
    agent = ChessPlayerAgent(mcp_client, color="white")
    run_server(agent, port=8001)
```

## A2A Client Implementation

### Basic Client for Chess Agents

```python
from python_a2a import A2AClient, Message, TextContent, MessageRole

class ChessA2AClient:
    def __init__(self, agent_url: str):
        self.client = A2AClient(agent_url)
    
    async def request_move(self, fen: str, pgn_history: str = "") -> str:
        """Request a move from a chess player agent"""
        message_text = f"Generate move for FEN: {fen}"
        if pgn_history:
            message_text += f" PGN: {pgn_history}"
        
        message = Message(
            content=TextContent(text=message_text),
            role=MessageRole.USER
        )
        
        response = self.client.send_message(message)
        return response.content.text
    
    async def validate_move(self, fen: str, move: str) -> bool:
        """Validate a move with a chess agent"""
        message = Message(
            content=TextContent(text=f"Validate move {move} for FEN: {fen}"),
            role=MessageRole.USER
        )
        
        response = self.client.send_message(message)
        return "valid" in response.content.text.lower()

# Usage in orchestrator
class ChessOrchestrator:
    def __init__(self):
        self.white_agent = ChessA2AClient("http://white-player-agent:8001/a2a")
        self.black_agent = ChessA2AClient("http://black-player-agent:8002/a2a")
    
    async def play_turn(self, session_id: str, fen: str, current_player: str):
        """Play a turn in the chess game"""
        if current_player == "white":
            move = await self.white_agent.request_move(fen)
        else:
            move = await self.black_agent.request_move(fen)
        
        # Validate move
        is_valid = await self.validate_move_with_agent(fen, move)
        
        if is_valid:
            # Apply move and update game state
            return await self.apply_move_to_session(session_id, move)
        else:
            raise ValueError(f"Invalid move generated: {move}")
```

## Agent Network Coordination

### Multi-Agent Chess System

```python
from python_a2a import AgentNetwork

class ChessGameNetwork:
    def __init__(self):
        self.network = AgentNetwork(name="Chess Game Network")
        
        # Register all chess agents
        self.network.add("orchestrator", "http://orchestrator-agent:8000")
        self.network.add("white_player", "http://white-player-agent:8001") 
        self.network.add("black_player", "http://black-player-agent:8002")
        self.network.add("mcp_server", "http://mcp-chess-server:8003")
    
    async def start_game(self, session_id: str, white_player: str = "ai", black_player: str = "ai"):
        """Start a new chess game"""
        orchestrator = self.network.get_agent("orchestrator")
        
        request = f"""
        Start new chess game:
        Session ID: {session_id}
        White Player: {white_player}
        Black Player: {black_player}
        Initial Position: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
        """
        
        response = orchestrator.ask(request)
        return response
    
    async def request_move(self, session_id: str, current_fen: str, current_turn: str):
        """Request move from appropriate player agent"""
        agent_name = f"{current_turn}_player"
        player_agent = self.network.get_agent(agent_name)
        
        request = f"""
        Generate move for position:
        Session ID: {session_id}
        FEN: {current_fen}
        Color: {current_turn}
        """
        
        response = player_agent.ask(request)
        return response
```

## Chess-Specific A2A Implementations

### 1. Chess Player Agent

```python
from python_a2a import A2AServer, skill, agent, run_server, TaskStatus, TaskState
import asyncio

@agent(
    name="Chess Player Agent",
    description="AI chess player using Stockfish engine via MCP",
    version="1.0.0"
)
class ChessPlayerAgent(A2AServer):
    
    def __init__(self, mcp_client, color, **kwargs):
        super().__init__(**kwargs)
        self.mcp_client = mcp_client
        self.color = color
    
    @skill(
        name="Generate Chess Move",
        description="Generate the best chess move for a given position",
        tags=["chess", "move", "strategy"],
        examples=["Generate move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"]
    )
    async def generate_move(self, fen: str, elo: int = 1500):
        """Generate chess move using MCP tools"""
        try:
            result = await self.mcp_client.get_best_move(fen, elo)
            
            if "error" in result:
                return f"Error generating move: {result['error']}"
            
            best_move = result.get("best_move")
            evaluation = result.get("evaluation", 0)
            
            return {
                "move": best_move,
                "evaluation": evaluation,
                "color": self.color,
                "fen": fen
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @skill(
        name="Validate Chess Move",
        description="Validate if a chess move is legal in given position",
        tags=["chess", "validation"],
        examples=["Validate move e2e4 for starting position"]
    )
    async def validate_move(self, fen: str, move: str):
        """Validate move using MCP tools"""
        try:
            result = await self.mcp_client.validate_move(fen, move)
            return {
                "valid": result.get("valid", False),
                "move": move,
                "fen": fen,
                "details": result
            }
        except Exception as e:
            return {"error": str(e)}
    
    def handle_task(self, task):
        """Handle incoming A2A tasks"""
        message_data = task.message or {}
        content = message_data.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""
        
        try:
            if "generate move" in text.lower():
                # Extract FEN from message
                fen = self._extract_fen_from_text(text)
                result = asyncio.run(self.generate_move(fen))
                
            elif "validate move" in text.lower():
                fen, move = self._extract_fen_and_move_from_text(text)
                result = asyncio.run(self.validate_move(fen, move))
                
            else:
                result = f"I'm a {self.color} chess player. Ask me to 'generate move' or 'validate move'."
            
            task.artifacts = [{
                "parts": [{"type": "text", "text": str(result)}]
            }]
            task.status = TaskStatus(state=TaskState.COMPLETED)
            
        except Exception as e:
            task.artifacts = [{
                "parts": [{"type": "text", "text": f"Error: {str(e)}"}]
            }]
            task.status = TaskStatus(state=TaskState.FAILED)
        
        return task
    
    def _extract_fen_from_text(self, text: str) -> str:
        """Extract FEN from message text"""
        if "fen:" in text.lower():
            fen_part = text.lower().split("fen:")[1].strip()
            fen_components = fen_part.split()[:6]  # FEN has 6 components
            return " ".join(fen_components)
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # Default starting position
    
    def _extract_fen_and_move_from_text(self, text: str) -> tuple:
        """Extract FEN and move from message text"""
        fen = self._extract_fen_from_text(text)
        
        # Extract move
        move = "e2e4"  # Default, should parse from text
        if "move:" in text.lower():
            move = text.lower().split("move:")[1].strip().split()[0]
        
        return fen, move
```

### 2. Chess Orchestrator Agent

```python
@agent(
    name="Chess Orchestrator",
    description="Manages chess games between multiple agents",
    version="1.0.0"
)
class ChessOrchestratorAgent(A2AServer):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sessions = {}  # Session management
        self.agent_network = AgentNetwork(name="Chess Network")
        self.agent_network.add("white_player", "http://white-player-agent:8001")
        self.agent_network.add("black_player", "http://black-player-agent:8002")
    
    @skill(
        name="Start Game",
        description="Start a new chess game session",
        tags=["chess", "game", "start"],
        examples=["Start game for session abc123"]
    )
    async def start_game(self, session_id: str):
        """Start a new chess game"""
        self.sessions[session_id] = {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "pgn": "",
            "turn": "white",
            "move_history": [],
            "status": "active"
        }
        
        return f"Game started for session {session_id}"
    
    @skill(
        name="Play Turn",
        description="Execute a turn in the chess game",
        tags=["chess", "turn", "move"],
        examples=["Play turn for session abc123"]
    )
    async def play_turn(self, session_id: str):
        """Play one turn of the chess game"""
        if session_id not in self.sessions:
            return f"No game found for session {session_id}"
        
        session = self.sessions[session_id]
        current_turn = session["turn"]
        current_fen = session["fen"]
        
        # Request move from appropriate agent
        player_agent = self.agent_network.get_agent(f"{current_turn}_player")
        move_request = f"Generate move for FEN: {current_fen}"
        
        move_response = player_agent.ask(move_request)
        
        # Parse move from response (simplified)
        move = self._parse_move_from_response(move_response)
        
        # Apply move and update session
        # (This would integrate with MCP server for move application)
        session["move_history"].append(move)
        session["turn"] = "black" if current_turn == "white" else "white"
        
        return f"Turn completed. Move: {move}"
    
    def handle_task(self, task):
        """Handle orchestrator tasks"""
        message_data = task.message or {}
        content = message_data.get("content", {})
        text = content.get("text", "") if isinstance(content, dict) else ""
        
        try:
            if "start game" in text.lower():
                session_id = self._extract_session_id(text)
                result = asyncio.run(self.start_game(session_id))
                
            elif "play turn" in text.lower():
                session_id = self._extract_session_id(text)
                result = asyncio.run(self.play_turn(session_id))
                
            else:
                result = "I'm the chess orchestrator. Ask me to 'start game' or 'play turn'."
            
            task.artifacts = [{
                "parts": [{"type": "text", "text": result}]
            }]
            task.status = TaskStatus(state=TaskState.COMPLETED)
            
        except Exception as e:
            task.artifacts = [{
                "parts": [{"type": "text", "text": f"Error: {str(e)}"}]
            }]
            task.status = TaskStatus(state=TaskState.FAILED)
        
        return task
```

## Docker Deployment for A2A Agents

### Individual Agent Containers

```dockerfile
# Dockerfile.chess-player-agent
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy agent code
COPY chess_player_agent.py .
COPY mcp_client.py .

# Create non-root user
RUN useradd -m -u 1000 agent
USER agent

# Expose port
EXPOSE 8001

# Run agent
CMD ["python", "chess_player_agent.py"]
```

### Docker Compose for Multi-Agent System

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-chess-server:
    build: ./mcp-server
    ports:
      - "8003:8000"
    environment:
      - STOCKFISH_PATH=/usr/games/stockfish
    restart: unless-stopped
    
  orchestrator-agent:
    build: 
      context: .
      dockerfile: Dockerfile.orchestrator
    ports:
      - "8000:8000"
    environment:
      - MCP_SERVER_URL=http://mcp-chess-server:8000
      - WHITE_AGENT_URL=http://white-player-agent:8001
      - BLACK_AGENT_URL=http://black-player-agent:8002
    depends_on:
      - mcp-chess-server
    restart: unless-stopped
    
  white-player-agent:
    build:
      context: .
      dockerfile: Dockerfile.chess-player-agent
    ports:
      - "8001:8001"
    environment:
      - MCP_SERVER_URL=http://mcp-chess-server:8000
      - AGENT_COLOR=white
    depends_on:
      - mcp-chess-server
    restart: unless-stopped
    
  black-player-agent:
    build:
      context: .
      dockerfile: Dockerfile.chess-player-agent
    ports:
      - "8002:8002" 
    environment:
      - MCP_SERVER_URL=http://mcp-chess-server:8000
      - AGENT_COLOR=black
    depends_on:
      - mcp-chess-server
    restart: unless-stopped
    
  gradio-web-app:
    build: ./web-app
    ports:
      - "7860:7860"
    environment:
      - ORCHESTRATOR_URL=http://orchestrator-agent:8000
    depends_on:
      - orchestrator-agent
    restart: unless-stopped

networks:
  default:
    name: chess-network
```

## Integration Patterns for Chess System

### 1. Agent Discovery

```python
# Agent discovery for chess system
class ChessAgentDiscovery:
    def __init__(self):
        self.agents = {}
    
    async def discover_chess_agents(self):
        """Discover all chess-related agents"""
        agent_urls = [
            "http://orchestrator-agent:8000",
            "http://white-player-agent:8001", 
            "http://black-player-agent:8002"
        ]
        
        for url in agent_urls:
            try:
                client = A2AClient(url)
                agent_card = client.agent_card
                self.agents[agent_card.name] = {
                    "url": url,
                    "capabilities": agent_card.capabilities,
                    "skills": [skill.name for skill in agent_card.skills]
                }
            except Exception as e:
                print(f"Failed to discover agent at {url}: {e}")
        
        return self.agents
```

### 2. Error Handling and Resilience

```python
class ResilientA2AClient:
    def __init__(self, agent_url: str, max_retries: int = 3):
        self.agent_url = agent_url
        self.max_retries = max_retries
        self.client = None
    
    async def send_message_with_retry(self, message: str) -> str:
        """Send message with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if not self.client:
                    self.client = A2AClient(self.agent_url)
                
                response = self.client.ask(message)
                return response
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                self.client = None  # Reset client on error
        
        raise Exception(f"Failed to send message after {self.max_retries} attempts")
```

## Key Implementation Recommendations

### 1. For Chess Player Agents
- Use `python-a2a` library for simplicity
- Implement chess-specific skills (generate_move, validate_move)
- Integrate with MCP client for Stockfish access
- Handle FEN and move parsing in task handlers
- Provide detailed error messages and fallbacks

### 2. For Chess Orchestrator
- Use AgentNetwork for coordinating multiple agents
- Implement session management for multiple concurrent games
- Handle turn-based communication between player agents
- Integrate with WebSocket for real-time web interface updates
- Maintain complete game state and history

### 3. For Production Deployment
- Use Docker containers for each agent
- Implement health checks and monitoring
- Configure proper networking between containers
- Use environment variables for configuration
- Implement retry logic and circuit breakers for resilience

### 4. Message Format Standards

```python
# Standard A2A message format for chess
chess_move_request = {
    "role": "user",
    "parts": [
        {
            "type": "text", 
            "text": "Generate move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        }
    ]
}

chess_move_response = {
    "role": "agent",
    "parts": [
        {
            "type": "text",
            "text": "Best move: e2e4 (Evaluation: +0.3)"
        }
    ]
}
```

This A2A implementation provides a robust foundation for agent communication in our multi-agent chess system, enabling seamless coordination between the orchestrator, player agents, and MCP services.