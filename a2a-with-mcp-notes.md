# A2A + External MCP Server Integration Notes

## Overview

Detailed notes on integrating A2A agents with external MCP servers based on "The Power Duo: How A2A + MCP Let You Build Practical AI Systems Today" by Manoj Desai. This focuses on the practical architecture patterns for our chess system.

## Core Integration Architecture

### The Two-Tier Model
- **A2A Layer**: Agent-to-agent communication and coordination
- **MCP Layer**: Tool and capability access through external servers
- **Clean Separation**: MCP focuses on capabilities, A2A handles orchestration

```
┌─────────────┐    A2A     ┌─────────────┐    MCP     ┌─────────────┐
│ Orchestrator│ ◄──────── │ Chess Agent │ ◄──────── │ External    │
│   Agent     │           │             │           │ MCP Server  │
└─────────────┘           └─────────────┘           └─────────────┘
```

### Key Benefits
1. **Modular Design**: Components can be developed and deployed independently
2. **Reusability**: External MCP servers can serve multiple A2A agents
3. **Technology Flexibility**: Mix different languages and frameworks
4. **Clear Error Boundaries**: Failures isolated to specific components

## FastMCPAgent Pattern for External MCP Integration

### Basic Integration Setup

```python
from python_a2a import A2AServer, Message, TextContent, MessageRole
from python_a2a.mcp import FastMCPAgent

class ChessPlayerAgent(A2AServer, FastMCPAgent):
    """Chess player agent using external MCP server"""
    
    def __init__(self, color: str, external_mcp_url: str):
        # Initialize both parent classes
        A2AServer.__init__(self)
        FastMCPAgent.__init__(
            self,
            mcp_servers={"chess": external_mcp_url}  # Connect to external MCP
        )
        self.color = color
    
    async def handle_message_async(self, message):
        """Process A2A messages using external MCP tools"""
        try:
            if message.content.type == "text":
                text = message.content.text.lower()
                
                if "generate move" in text:
                    return await self._handle_move_generation(message)
                elif "validate move" in text:
                    return await self._handle_move_validation(message)
                else:
                    return self._default_response(message)
                    
        except Exception as e:
            return self._error_response(message, str(e))
    
    async def _handle_move_generation(self, message):
        """Generate move using external MCP chess tools"""
        # Extract FEN from A2A message
        fen = self._extract_fen_from_message(message.content.text)
        
        # Call external MCP tool
        result = await self.call_mcp_tool(
            "chess",                           # MCP server identifier
            "get_best_move_given_fen",        # Tool name
            fen=fen,                          # Tool parameters
            elo=1500
        )
        
        if "error" in result:
            response_text = f"Error generating move: {result['error']}"
        else:
            best_move = result.get("best_move", "No move")
            evaluation = result.get("evaluation", "Unknown")
            response_text = f"Best move for {self.color}: {best_move} (Eval: {evaluation})"
        
        return Message(
            content=TextContent(text=response_text),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id
        )
    
    async def _handle_move_validation(self, message):
        """Validate move using external MCP chess tools"""
        fen, move = self._extract_fen_and_move(message.content.text)
        
        # Call external MCP tool for validation
        result = await self.call_mcp_tool(
            "chess",
            "is_move_valid_given_fen",
            fen=fen,
            move_uci=move
        )
        
        is_valid = result.get("valid", False)
        response_text = f"Move {move} is {'valid' if is_valid else 'invalid'}"
        
        return Message(
            content=TextContent(text=response_text),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id
        )
```

## Multi-External MCP Server Integration

### Chess System with Multiple External MCP Servers

```python
class AdvancedChessAgent(A2AServer, FastMCPAgent):
    """Agent using multiple external MCP servers for different capabilities"""
    
    def __init__(self, color: str):
        # Discover external MCP servers from environment
        mcp_servers = {
            "chess_engine": os.getenv("CHESS_MCP_SERVER_URL", "http://mcp-chess-server:8000"),
            "opening_book": os.getenv("OPENING_MCP_SERVER_URL", "http://mcp-opening-server:8001"),
            "endgame_db": os.getenv("ENDGAME_MCP_SERVER_URL", "http://mcp-endgame-server:8002")
        }
        
        A2AServer.__init__(self)
        FastMCPAgent.__init__(self, mcp_servers=mcp_servers)
        self.color = color
    
    async def get_comprehensive_move_analysis(self, fen: str, pgn_history: str = ""):
        """Analyze position using multiple external MCP servers"""
        
        analysis_results = {}
        
        # 1. Check opening book first (if early in game)
        try:
            if len(pgn_history.split()) < 20:  # Early game
                opening_result = await self.call_mcp_tool(
                    "opening_book",
                    "get_opening_move",
                    fen=fen,
                    pgn_history=pgn_history
                )
                analysis_results["opening"] = opening_result
        except:
            pass  # Opening book optional
        
        # 2. Get engine analysis
        try:
            engine_result = await self.call_mcp_tool(
                "chess_engine",
                "get_best_move_given_fen",
                fen=fen,
                depth=20
            )
            analysis_results["engine"] = engine_result
        except Exception as e:
            analysis_results["engine"] = {"error": str(e)}
        
        # 3. Check endgame database (if few pieces)
        try:
            piece_count = fen.count('K') + fen.count('Q') + fen.count('R') + \
                         fen.count('B') + fen.count('N') + fen.count('P') + \
                         fen.count('k') + fen.count('q') + fen.count('r') + \
                         fen.count('b') + fen.count('n') + fen.count('p')
            
            if piece_count <= 8:  # Endgame
                endgame_result = await self.call_mcp_tool(
                    "endgame_db",
                    "query_endgame_database",
                    fen=fen
                )
                analysis_results["endgame"] = endgame_result
        except:
            pass  # Endgame DB optional
        
        # 4. Combine results and choose best move
        return self._select_best_move_from_analysis(analysis_results, fen)
    
    def _select_best_move_from_analysis(self, analysis_results: dict, fen: str) -> dict:
        """Select best move from multiple analysis sources"""
        
        # Priority: Endgame DB > Opening Book > Engine
        if "endgame" in analysis_results and "move" in analysis_results["endgame"]:
            return {
                "best_move": analysis_results["endgame"]["move"],
                "source": "endgame_database",
                "confidence": "high"
            }
        
        if "opening" in analysis_results and "move" in analysis_results["opening"]:
            return {
                "best_move": analysis_results["opening"]["move"],
                "source": "opening_book", 
                "confidence": "high"
            }
        
        if "engine" in analysis_results and "best_move" in analysis_results["engine"]:
            return {
                "best_move": analysis_results["engine"]["best_move"],
                "evaluation": analysis_results["engine"].get("evaluation"),
                "source": "chess_engine",
                "confidence": "medium"
            }
        
        # Fallback
        return {
            "best_move": "e2e4" if "w" in fen else "e7e5",
            "source": "fallback",
            "confidence": "low"
        }
```

## Chess Orchestrator with External MCP Integration

### Complete Orchestrator Implementation

```python
from python_a2a import A2AServer, AgentNetwork, A2AClient
from python_a2a.mcp import FastMCPAgent
import os
import asyncio

class ChessOrchestratorAgent(A2AServer, FastMCPAgent):
    """Orchestrator managing chess games using external MCP and A2A agents"""
    
    def __init__(self):
        # External MCP server for chess operations
        chess_mcp_url = os.getenv("CHESS_MCP_SERVER_URL", "http://mcp-chess-server:8000")
        
        A2AServer.__init__(self)
        FastMCPAgent.__init__(
            self,
            mcp_servers={"chess": chess_mcp_url}
        )
        
        # A2A agent network for player agents
        self.agent_network = AgentNetwork(name="Chess Game Network")
        self.agent_network.add("white_player", os.getenv("WHITE_AGENT_URL", "http://white-player-agent:8001"))
        self.agent_network.add("black_player", os.getenv("BLACK_AGENT_URL", "http://black-player-agent:8002"))
        
        self.sessions = {}  # Game session management
    
    async def start_new_game(self, session_id: str):
        """Start new chess game using external MCP for validation"""
        starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Validate starting position via external MCP
        status = await self.call_mcp_tool(
            "chess",
            "check_game_end_conditions",
            fen=starting_fen
        )
        
        if "error" not in status:
            self.sessions[session_id] = {
                "fen": starting_fen,
                "turn": "white",
                "move_history": [],
                "pgn_history": "",
                "status": "active",
                "created_at": asyncio.get_event_loop().time()
            }
            return f"Chess game {session_id} started successfully"
        else:
            return f"Error starting game: {status['error']}"
    
    async def process_game_turn(self, session_id: str):
        """Process one complete turn using A2A agents and external MCP"""
        
        if session_id not in self.sessions:
            return {"error": "Game session not found"}
        
        session = self.sessions[session_id]
        current_turn = session["turn"]
        current_fen = session["fen"]
        pgn_history = session["pgn_history"]
        
        try:
            # Step 1: Request move from A2A player agent
            player_agent = self.agent_network.get_agent(f"{current_turn}_player")
            move_request = f"Generate move for FEN: {current_fen} PGN: {pgn_history}"
            
            move_response = player_agent.ask(move_request)
            move = self._parse_move_from_a2a_response(move_response)
            
            # Step 2: Validate move using external MCP server
            validation = await self.call_mcp_tool(
                "chess",
                "is_move_valid_given_fen",
                fen=current_fen,
                move_uci=move
            )
            
            if not validation.get("valid", False):
                return {"error": f"Invalid move from {current_turn} agent: {move}"}
            
            # Step 3: Apply move using external MCP server
            result = await self.call_mcp_tool(
                "chess",
                "apply_move_to_position",
                fen=current_fen,
                move_uci=move
            )
            
            if "error" in result:
                return {"error": f"Error applying move: {result['error']}"}
            
            # Step 4: Update session state
            new_fen = result["new_fen"]
            move_san = result["move_san"]
            
            session["fen"] = new_fen
            session["move_history"].append({
                "player": current_turn,
                "move_uci": move,
                "move_san": move_san,
                "fen_after": new_fen,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Update PGN history
            if session["pgn_history"]:
                session["pgn_history"] += f" {move_san}"
            else:
                session["pgn_history"] = move_san
            
            # Step 5: Check game end using external MCP
            game_status = await self.call_mcp_tool(
                "chess",
                "check_game_end_conditions",
                fen=new_fen
            )
            
            if game_status.get("game_over", False):
                session["status"] = "finished"
                session["result"] = {
                    "winner": game_status.get("winner"),
                    "termination": game_status.get("termination"),
                    "final_fen": new_fen
                }
                
                return {
                    "turn_completed": True,
                    "move": move_san,
                    "game_finished": True,
                    "result": session["result"],
                    "session_id": session_id
                }
            else:
                # Switch turns
                session["turn"] = "black" if current_turn == "white" else "white"
                
                return {
                    "turn_completed": True,
                    "move": move_san,
                    "game_finished": False,
                    "next_turn": session["turn"],
                    "position": new_fen,
                    "session_id": session_id
                }
                
        except Exception as e:
            return {"error": f"Turn processing failed: {str(e)}"}
    
    def _parse_move_from_a2a_response(self, response: str) -> str:
        """Extract chess move from A2A agent response"""
        import re
        
        # Look for move patterns in response
        move_patterns = [
            r'move[:\s]*([a-h][1-8][a-h][1-8][qrbn]?)',  # UCI format
            r'best move[:\s]*([a-h][1-8][a-h][1-8][qrbn]?)',
            r'([a-h][1-8][a-h][1-8][qrbn]?)'  # Standalone UCI
        ]
        
        for pattern in move_patterns:
            match = re.search(pattern, response.lower())
            if match:
                return match.group(1)
        
        # Fallback - extract from JSON if structured response
        try:
            import json
            data = json.loads(response)
            if "move" in data:
                return data["move"]
        except:
            pass
        
        raise ValueError(f"Could not parse move from response: {response}")
```

## Environment-Based MCP Server Discovery

### Dynamic MCP Server Configuration

```python
import os
from typing import Dict, Optional

class MCPServerDiscovery:
    """Discover and manage external MCP servers via environment"""
    
    @staticmethod
    def discover_chess_mcp_servers() -> Dict[str, str]:
        """Discover available chess-related MCP servers"""
        servers = {}
        
        # Core chess engine (required)
        chess_mcp_url = os.getenv("CHESS_MCP_SERVER_URL")
        if chess_mcp_url:
            servers["chess_engine"] = chess_mcp_url
        
        # Optional specialized servers
        optional_servers = {
            "opening_book": "OPENING_MCP_SERVER_URL",
            "endgame_db": "ENDGAME_MCP_SERVER_URL", 
            "position_analysis": "ANALYSIS_MCP_SERVER_URL",
            "puzzle_solver": "PUZZLE_MCP_SERVER_URL"
        }
        
        for server_name, env_var in optional_servers.items():
            url = os.getenv(env_var)
            if url:
                servers[server_name] = url
        
        return servers
    
    @staticmethod
    async def test_mcp_server_availability(servers: Dict[str, str]) -> Dict[str, bool]:
        """Test which MCP servers are actually available"""
        import httpx
        
        availability = {}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for server_name, url in servers.items():
                try:
                    # Test health endpoint
                    response = await client.get(f"{url}/health")
                    health_data = response.json()
                    availability[server_name] = health_data.get("status") == "healthy"
                except:
                    availability[server_name] = False
        
        return availability

class AdaptiveChessAgent(A2AServer, FastMCPAgent):
    """Chess agent that adapts to available external MCP servers"""
    
    def __init__(self, color: str):
        # Discover available MCP servers
        self.available_servers = MCPServerDiscovery.discover_chess_mcp_servers()
        
        if not self.available_servers:
            raise ValueError("No chess MCP servers configured")
        
        A2AServer.__init__(self)
        FastMCPAgent.__init__(self, mcp_servers=self.available_servers)
        self.color = color
        self.server_capabilities = {}
    
    async def initialize_server_capabilities(self):
        """Test and catalog available server capabilities"""
        availability = await MCPServerDiscovery.test_mcp_server_availability(self.available_servers)
        
        self.server_capabilities = {
            "move_generation": availability.get("chess_engine", False),
            "opening_book": availability.get("opening_book", False),
            "endgame_analysis": availability.get("endgame_db", False),
            "position_analysis": availability.get("position_analysis", False)
        }
        
        print(f"Available capabilities: {self.server_capabilities}")
    
    async def get_best_move_adaptive(self, fen: str, pgn_history: str = ""):
        """Get best move using available external MCP servers"""
        
        # Strategy 1: Use opening book if available and applicable
        if self.server_capabilities.get("opening_book") and len(pgn_history.split()) < 20:
            try:
                result = await self.call_mcp_tool(
                    "opening_book",
                    "get_opening_move",
                    fen=fen,
                    pgn_history=pgn_history
                )
                if "move" in result:
                    return {"move": result["move"], "source": "opening_book"}
            except:
                pass
        
        # Strategy 2: Use endgame database if applicable
        if self.server_capabilities.get("endgame_analysis"):
            piece_count = sum(1 for c in fen if c.isalpha())
            if piece_count <= 8:
                try:
                    result = await self.call_mcp_tool(
                        "endgame_db",
                        "query_endgame_position",
                        fen=fen
                    )
                    if "move" in result:
                        return {"move": result["move"], "source": "endgame_database"}
                except:
                    pass
        
        # Strategy 3: Use chess engine (fallback)
        if self.server_capabilities.get("move_generation"):
            try:
                result = await self.call_mcp_tool(
                    "chess_engine",
                    "get_best_move_given_fen",
                    fen=fen
                )
                return {
                    "move": result.get("best_move"),
                    "evaluation": result.get("evaluation"),
                    "source": "chess_engine"
                }
            except Exception as e:
                return {"error": f"Engine failed: {str(e)}"}
        
        # Ultimate fallback
        return {
            "move": "e2e4" if "w" in fen else "e7e5",
            "source": "hardcoded_fallback"
        }
```

## Docker Configuration for External MCP Integration

### Environment-Based Configuration

```dockerfile
# Dockerfile.chess-agent
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy agent code
COPY chess_agent.py .

# Create non-root user
RUN useradd -m -u 1000 agent
USER agent

# Environment variables for external MCP server discovery
ENV CHESS_MCP_SERVER_URL=http://mcp-chess-server:8000
ENV OPENING_MCP_SERVER_URL=http://mcp-opening-server:8001
ENV ENDGAME_MCP_SERVER_URL=http://mcp-endgame-server:8002

# A2A agent port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Run agent
CMD ["python", "chess_agent.py"]
```

### Complete Docker Compose with External MCP

```yaml
# docker-compose.yml
version: '3.8'

networks:
  chess-network:
    driver: bridge

services:
  # External MCP Servers (Independent Services)
  mcp-chess-engine:
    image: chess-mcp-server:latest
    ports:
      - "8003:8000"
    environment:
      - STOCKFISH_PATH=/usr/games/stockfish
      - LOG_LEVEL=info
    networks:
      - chess-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  mcp-opening-book:
    image: opening-book-mcp:latest
    ports:
      - "8004:8000"
    environment:
      - OPENING_DB_PATH=/data/openings.db
    networks:
      - chess-network
    restart: unless-stopped
    
  mcp-endgame-db:
    image: endgame-mcp:latest
    ports:
      - "8005:8000"
    environment:
      - TABLEBASE_PATH=/data/syzygy
    networks:
      - chess-network
    restart: unless-stopped
  
  # A2A Agents (Using External MCP Servers)
  orchestrator-agent:
    build:
      context: .
      dockerfile: Dockerfile.orchestrator
    ports:
      - "8000:8000"
    environment:
      # External MCP server URLs
      - CHESS_MCP_SERVER_URL=http://mcp-chess-engine:8000
      - OPENING_MCP_SERVER_URL=http://mcp-opening-book:8000
      - ENDGAME_MCP_SERVER_URL=http://mcp-endgame-db:8000
      # A2A agent URLs
      - WHITE_AGENT_URL=http://white-player-agent:8001
      - BLACK_AGENT_URL=http://black-player-agent:8002
    depends_on:
      - mcp-chess-engine
      - white-player-agent
      - black-player-agent
    networks:
      - chess-network
    restart: unless-stopped
    
  white-player-agent:
    build:
      context: .
      dockerfile: Dockerfile.chess-agent
    ports:
      - "8001:8001"
    environment:
      - AGENT_COLOR=white
      - AGENT_PORT=8001
      # External MCP servers
      - CHESS_MCP_SERVER_URL=http://mcp-chess-engine:8000
      - OPENING_MCP_SERVER_URL=http://mcp-opening-book:8000
      - ENDGAME_MCP_SERVER_URL=http://mcp-endgame-db:8000
    depends_on:
      - mcp-chess-engine
    networks:
      - chess-network
    restart: unless-stopped
    
  black-player-agent:
    build:
      context: .
      dockerfile: Dockerfile.chess-agent
    ports:
      - "8002:8002"
    environment:
      - AGENT_COLOR=black
      - AGENT_PORT=8002
      # External MCP servers  
      - CHESS_MCP_SERVER_URL=http://mcp-chess-engine:8000
      - OPENING_MCP_SERVER_URL=http://mcp-opening-book:8000
      - ENDGAME_MCP_SERVER_URL=http://mcp-endgame-db:8000
    depends_on:
      - mcp-chess-engine
    networks:
      - chess-network
    restart: unless-stopped
    
  # Web Interface
  gradio-web-app:
    build: ./web-app
    ports:
      - "7860:7860"
    environment:
      - ORCHESTRATOR_URL=http://orchestrator-agent:8000
    depends_on:
      - orchestrator-agent
    networks:
      - chess-network
    restart: unless-stopped
```

## Error Handling and Resilience Patterns

### Health Checking and Circuit Breaker

```python
import time
from enum import Enum

class MCPServerState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

class MCPCircuitBreaker:
    """Circuit breaker for external MCP server calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = MCPServerState.HEALTHY
    
    async def call_with_circuit_breaker(self, mcp_call_func, *args, **kwargs):
        """Execute MCP call with circuit breaker protection"""
        
        # Check if circuit is open
        if self.state == MCPServerState.FAILED:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = MCPServerState.DEGRADED  # Try recovery
                self.failure_count = 0
            else:
                raise Exception("Circuit breaker open - MCP server unavailable")
        
        try:
            # Execute MCP call
            result = await mcp_call_func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == MCPServerState.DEGRADED:
                self.state = MCPServerState.HEALTHY
            self.failure_count = 0
            
            return result
            
        except Exception as e:
            # Handle failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = MCPServerState.FAILED
            
            raise e

class ResilientChessAgent(A2AServer, FastMCPAgent):
    """Chess agent with circuit breaker for external MCP calls"""
    
    def __init__(self, color: str):
        mcp_servers = MCPServerDiscovery.discover_chess_mcp_servers()
        
        A2AServer.__init__(self)
        FastMCPAgent.__init__(self, mcp_servers=mcp_servers)
        self.color = color
        
        # Circuit breakers for each MCP server
        self.circuit_breakers = {
            server_name: MCPCircuitBreaker()
            for server_name in mcp_servers.keys()
        }
    
    async def call_mcp_tool_safely(self, server_name: str, tool_name: str, **kwargs):
        """Call MCP tool with circuit breaker protection"""
        
        if server_name not in self.circuit_breakers:
            raise ValueError(f"Unknown MCP server: {server_name}")
        
        circuit_breaker = self.circuit_breakers[server_name]
        
        async def mcp_call():
            return await self.call_mcp_tool(server_name, tool_name, **kwargs)
        
        try:
            return await circuit_breaker.call_with_circuit_breaker(mcp_call)
        except Exception as e:
            print(f"MCP call failed for {server_name}/{tool_name}: {e}")
            return {"error": str(e)}
```

## Testing and Monitoring

### Integration Test Suite

```python
#!/usr/bin/env python3
# test_a2a_external_mcp.py

import asyncio
import httpx
from python_a2a import A2AClient
import time

class A2AMCPIntegrationTester:
    """Test suite for A2A + external MCP integration"""
    
    def __init__(self):
        self.mcp_servers = {
            "chess": "http://localhost:8003",
            "opening": "http://localhost:8004",
            "endgame": "http://localhost:8005"
        }
        self.a2a_agents = {
            "orchestrator": "http://localhost:8000",
            "white_player": "http://localhost:8001",
            "black_player": "http://localhost:8002"
        }
    
    async def test_mcp_server_health(self):
        """Test all external MCP servers"""
        print("Testing External MCP Server Health...")
        
        async with httpx.AsyncClient() as client:
            for name, url in self.mcp_servers.items():
                try:
                    response = await client.get(f"{url}/health", timeout=5.0)
                    health = response.json()
                    status = health.get("status", "unknown")
                    print(f"  {name}: {status}")
                except Exception as e:
                    print(f"  {name}: ERROR - {e}")
    
    async def test_a2a_agent_health(self):
        """Test all A2A agents"""
        print("\nTesting A2A Agent Health...")
        
        for name, url in self.a2a_agents.items():
            try:
                client = A2AClient(f"{url}/a2a")
                response = client.ask("health check")
                print(f"  {name}: OK")
            except Exception as e:
                print(f"  {name}: ERROR - {e}")
    
    async def test_move_generation_flow(self):
        """Test complete move generation via A2A → MCP flow"""
        print("\nTesting Move Generation Flow...")
        
        try:
            # Test white player agent
            white_client = A2AClient("http://localhost:8001/a2a")
            response = white_client.ask(
                "Generate move for FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            )
            print(f"  White Agent Response: {response}")
            
            # Test black player agent  
            black_client = A2AClient("http://localhost:8002/a2a")
            response = black_client.ask(
                "Generate move for FEN: rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
            )
            print(f"  Black Agent Response: {response}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    async def test_game_orchestration(self):
        """Test complete game orchestration"""
        print("\nTesting Game Orchestration...")
        
        try:
            orchestrator_client = A2AClient("http://localhost:8000/a2a")
            
            # Start game
            session_id = "test_session_123"
            response = orchestrator_client.ask(f"Start new game for session {session_id}")
            print(f"  Game Start: {response}")
            
            # Play a few turns
            for turn in range(3):
                response = orchestrator_client.ask(f"Play turn for session {session_id}")
                print(f"  Turn {turn + 1}: {response}")
                time.sleep(1)  # Brief pause between turns
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    async def run_full_test_suite(self):
        """Run complete test suite"""
        print("=== A2A + External MCP Integration Test Suite ===\n")
        
        await self.test_mcp_server_health()
        await self.test_a2a_agent_health()
        await self.test_move_generation_flow()
        await self.test_game_orchestration()
        
        print("\n=== Test Suite Complete ===")

async def main():
    tester = A2AMCPIntegrationTester()
    await tester.run_full_test_suite()

if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Monitoring

### MCP Performance Tracking

```python
class MCPPerformanceMonitor:
    """Monitor performance of external MCP server calls"""
    
    def __init__(self):
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_response_time": 0,
            "server_metrics": {}
        }
    
    async def monitored_mcp_call(self, server_name: str, tool_name: str, mcp_call_func, **kwargs):
        """Execute MCP call with performance monitoring"""
        
        start_time = time.time()
        
        try:
            result = await mcp_call_func(**kwargs)
            
            # Record success metrics
            response_time = time.time() - start_time
            self.metrics["total_calls"] += 1
            self.metrics["successful_calls"] += 1
            self.metrics["total_response_time"] += response_time
            
            # Server-specific metrics
            if server_name not in self.metrics["server_metrics"]:
                self.metrics["server_metrics"][server_name] = {
                    "calls": 0,
                    "successes": 0,
                    "total_time": 0
                }
            
            server_metrics = self.metrics["server_metrics"][server_name]
            server_metrics["calls"] += 1
            server_metrics["successes"] += 1
            server_metrics["total_time"] += response_time
            
            return result
            
        except Exception as e:
            # Record failure metrics
            self.metrics["total_calls"] += 1
            self.metrics["failed_calls"] += 1
            
            if server_name not in self.metrics["server_metrics"]:
                self.metrics["server_metrics"][server_name] = {"calls": 0, "successes": 0, "total_time": 0}
            
            self.metrics["server_metrics"][server_name]["calls"] += 1
            
            raise e
    
    def get_performance_report(self) -> dict:
        """Generate performance report"""
        if self.metrics["total_calls"] == 0:
            return {"status": "no_data"}
        
        avg_response_time = self.metrics["total_response_time"] / self.metrics["successful_calls"] if self.metrics["successful_calls"] > 0 else 0
        success_rate = self.metrics["successful_calls"] / self.metrics["total_calls"]
        
        return {
            "total_calls": self.metrics["total_calls"],
            "success_rate": f"{success_rate:.2%}",
            "average_response_time": f"{avg_response_time:.3f}s",
            "server_breakdown": self.metrics["server_metrics"]
        }
```

## Key Implementation Recommendations

### 1. For Chess System Integration

**External MCP Server Setup:**
- Deploy chess engine MCP server independently
- Optional: Deploy specialized MCP servers (opening book, endgame database)
- Use health checks and monitoring for all external servers

**A2A Agent Configuration:**
- Configure MCP server URLs via environment variables
- Implement fallback strategies for MCP server failures
- Use circuit breakers to prevent cascade failures

**Orchestrator Design:**
- Coordinate between A2A player agents and external MCP servers
- Maintain session state while leveraging stateless MCP tools
- Handle complex workflows (game start → move generation → validation → state update)

### 2. Production Deployment

**Service Independence:**
- MCP servers can be updated without affecting A2A agents
- A2A agents can be scaled independently
- Clear service boundaries enable team specialization

**Monitoring and Observability:**
- Health checks for all external MCP servers
- Performance monitoring for MCP tool calls
- Error tracking and alerting for integration points

**Error Handling:**
- Graceful degradation when external MCP servers unavailable
- Fallback strategies for critical chess operations
- Circuit breaker patterns to prevent system overload

This architecture provides a robust, scalable foundation for building multi-agent systems that leverage external capabilities while maintaining clear separation of concerns and fault tolerance.