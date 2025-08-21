# Multi-Agent Chess Playing Game - Technical Design Document

## 1. Executive Summary

This document outlines the technical architecture for a multi-agent chess playing system that leverages the Agent-to-Agent (A2A) protocol for inter-agent communication, Model Context Protocol (MCP) for chess engine integration, and modern web technologies for the user interface. The system consists of five main components: an orchestrator agent, two player agents (white and black), an MCP server with Stockfish integration, and a Gradio web application.

## 2. System Architecture Overview

### 2.1 High-Level Architecture

```mermaid
graph TB
    subgraph "Web Layer"
        WebApp[Gradio Web App<br/>Port: 7860]
        Browser[Web Browser<br/>User Interface]
    end
    
    subgraph "Agent Layer"
        Orchestrator[Orchestrator Agent<br/>Stateful<br/>Port: 8000]
        WhiteAgent[White Player Agent<br/>Stateless<br/>Port: 8001]
        BlackAgent[Black Player Agent<br/>Stateless<br/>Port: 8002]
    end
    
    subgraph "Chess Engine Layer"
        MCPServer[MCP Server<br/>Stockfish Interface<br/>Port: 8003]
        Stockfish[(Stockfish Engine)]
    end
    
    subgraph "Infrastructure"
        Docker[Docker Containers]
        Sliplane[Sliplane.io<br/>Deployment]
    end
    
    Browser <--> WebApp
    WebApp <--> Orchestrator
    Orchestrator <--> WhiteAgent
    Orchestrator <--> BlackAgent
    WhiteAgent <--> MCPServer
    BlackAgent <--> MCPServer
    MCPServer <--> Stockfish
    
    Docker --> WebApp
    Docker --> Orchestrator
    Docker --> WhiteAgent
    Docker --> BlackAgent
    Docker --> MCPServer
    Sliplane --> Docker
```

### 2.2 Component Responsibilities

| Component | Type | State | Primary Responsibilities |
|-----------|------|-------|-------------------------|
| **Orchestrator Agent** | Stateful | Persistent | Game state management, session handling, turn coordination, WebSocket server |
| **White Player Agent** | Stateless | Request-scoped | Generate moves for white pieces, move analysis |
| **Black Player Agent** | Stateless | Request-scoped | Generate moves for black pieces, move analysis |
| **MCP Server** | Stateless | Request-scoped | Chess engine integration, move validation, position analysis |
| **Gradio Web App** | Stateful | Session-based | User interface, game visualization, WebSocket client |

## 3. Communication Protocols

### 3.1 Protocol Stack

```mermaid
graph LR
    subgraph "Communication Protocols"
        A2A[A2A Protocol<br/>Agent-to-Agent]
        MCP[MCP Protocol<br/>Model Context Protocol]
        WS[WebSocket<br/>Real-time Updates]
        HTTP[HTTP/REST<br/>Web API]
    end
    
    subgraph "Message Formats"
        JSON[JSON Payloads]
        FEN[FEN Board Notation]
        PGN[PGN Move History]
    end
    
    A2A --> JSON
    MCP --> JSON
    WS --> JSON
    HTTP --> JSON
    JSON --> FEN
    JSON --> PGN
```

### 3.2 Message Flow Patterns

```mermaid
sequenceDiagram
    participant W as Web App
    participant O as Orchestrator
    participant P as Player Agent
    participant M as MCP Server
    participant S as Stockfish
    
    Note over W,S: Communication Protocol Stack
    W->>O: WebSocket/JSON
    O->>P: A2A Protocol/JSON
    P->>M: MCP Protocol/JSON
    M->>S: Native Stockfish API
```

## 4. Detailed Sequence Diagrams

### 4.1 Game Initialization Flow

```mermaid
sequenceDiagram
    participant User as Web Browser
    participant WebApp as Gradio App
    participant Orch as Orchestrator
    participant WhiteAgent as White Agent
    participant BlackAgent as Black Agent
    participant MCP as MCP Server
    
    User->>WebApp: Open chess game page
    WebApp->>WebApp: Generate session ID
    WebApp->>Orch: WebSocket connect (session_id)
    Orch->>Orch: Create/resume game session
    
    alt New Game
        User->>WebApp: Click "Start New Game"
        WebApp->>Orch: {"action": "start_game", "session_id": "abc123"}
        Orch->>Orch: Initialize board (FEN: starting position)
        Orch->>Orch: Create PGN header
        Orch->>WebApp: {"event": "game_started", "board_fen": "...", "turn": "white"}
        WebApp->>User: Display initial board
    else Resume Game
        Orch->>Orch: Load existing game state
        Orch->>WebApp: {"event": "game_resumed", "board_fen": "...", "pgn": "...", "turn": "..."}
        WebApp->>User: Display current board state
    end
    
    Note over User,MCP: Game ready for first move
```

### 4.2 Move Processing Flow

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Player as Player Agent
    participant MCP as MCP Server
    participant Stockfish as Stockfish Engine
    participant WebApp as Gradio App
    
    Orch->>Player: A2A: {"action": "request_move", "fen": "...", "pgn": "...", "color": "white"}
    
    Player->>MCP: MCP: get_best_move_given_history_in_pgn(pgn_history)
    MCP->>Stockfish: analyze position
    Stockfish-->>MCP: best_move: "e2e4"
    MCP-->>Player: {"best_move": "e2e4", "evaluation": "+0.3"}
    
    Player->>MCP: MCP: is_move_valid_given_fen(fen, "e2e4")
    MCP->>Stockfish: validate move
    Stockfish-->>MCP: valid: true
    MCP-->>Player: {"valid": true}
    
    Player-->>Orch: A2A: {"move": "e2e4", "confidence": 0.95}
    
    Orch->>Orch: Validate move against current state
    Orch->>Orch: Apply move to board
    Orch->>Orch: Update PGN history
    Orch->>Orch: Check game end conditions
    
    Orch->>WebApp: WebSocket: {"event": "move_played", "move": "e2e4", "fen": "...", "pgn": "..."}
    WebApp->>WebApp: Animate move on board
    
    alt Game Continues
        Orch->>Orch: Switch turn to black
        Note over Orch: Process next move
    else Game Ends
        Orch->>WebApp: WebSocket: {"event": "game_ended", "result": "1-0", "reason": "checkmate"}
        Orch->>Orch: Save final game state
    end
```

### 4.3 Error Handling Flow

```mermaid
sequenceDiagram
    participant Orch as Orchestrator
    participant Player as Player Agent
    participant MCP as MCP Server
    
    Orch->>Player: A2A: request_move
    
    Player->>MCP: get_best_move_given_history_in_pgn
    MCP-->>Player: Error: Engine timeout
    
    Player->>Player: Fallback: Use simple evaluation
    Player->>MCP: is_move_valid_given_fen
    MCP-->>Player: {"valid": true}
    
    Player-->>Orch: {"move": "fallback_move", "note": "engine_timeout"}
    
    alt Move Valid
        Orch->>Orch: Process move normally
    else Move Invalid
        Orch->>Player: A2A: {"error": "invalid_move", "retry": true}
        Player->>Player: Generate alternative move
        Player-->>Orch: {"move": "alternative_move"}
    end
    
    alt Max Retries Exceeded
        Orch->>Orch: Forfeit game for player
        Orch->>WebApp: {"event": "game_ended", "result": "forfeit"}
    end
```

## 5. Data Models and Schemas

### 5.1 Core Data Structures

```mermaid
classDiagram
    class GameSession {
        +string session_id
        +string game_id
        +DateTime created_at
        +DateTime updated_at
        +GameState current_state
        +GameMetadata metadata
        +List~Move~ move_history
        +GameStatus status
    }
    
    class GameState {
        +string fen
        +string pgn
        +Color current_turn
        +int move_number
        +CastlingRights castling_rights
        +string en_passant_target
        +int halfmove_clock
        +int fullmove_number
    }
    
    class GameMetadata {
        +string white_player
        +string black_player
        +DateTime start_time
        +int time_control
        +string event_name
        +string site
    }
    
    class Move {
        +string from_square
        +string to_square
        +string piece
        +string notation
        +DateTime timestamp
        +float engine_evaluation
        +int move_number
    }
    
    GameSession --> GameState
    GameSession --> GameMetadata
    GameSession --> Move
```

### 5.2 Message Schemas

#### A2A Protocol Messages

```json
// Move Request (Orchestrator → Player Agent)
{
  "message_type": "move_request",
  "session_id": "abc123",
  "game_id": "game_456",
  "current_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "pgn_history": "1. e4 e5 2. Nf3",
  "color": "white",
  "time_remaining": 300000,
  "timestamp": "2024-01-01T12:00:00Z"
}

// Move Response (Player Agent → Orchestrator)
{
  "message_type": "move_response",
  "session_id": "abc123",
  "move": "Nc3",
  "move_uci": "b1c3",
  "confidence": 0.87,
  "engine_evaluation": "+0.15",
  "thinking_time": 2.5,
  "timestamp": "2024-01-01T12:00:02Z"
}
```

#### MCP Tool Schemas

```json
// get_best_move_given_history_in_pgn
{
  "tool": "get_best_move_given_history_in_pgn",
  "parameters": {
    "pgn_history": "1. e4 e5 2. Nf3 Nc6",
    "depth": 15,
    "time_limit": 5.0
  }
}

// is_move_valid_given_fen
{
  "tool": "is_move_valid_given_fen",
  "parameters": {
    "fen": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    "move_uci": "f1c4"
  }
}
```

#### WebSocket Messages

```json
// Game State Update
{
  "event": "game_state_update",
  "session_id": "abc123",
  "board_fen": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
  "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4",
  "current_turn": "black",
  "move_number": 3,
  "last_move": {
    "from": "f1",
    "to": "c4",
    "piece": "bishop",
    "notation": "Bc4"
  },
  "game_status": "active"
}
```

## 6. Deployment Architecture

### 6.1 Container Architecture

```mermaid
graph TB
    subgraph "Sliplane.io Deployment"
        subgraph "Container Network"
            subgraph "Web Tier"
                GradioContainer[Gradio Container<br/>gradio-chess-app<br/>Port: 7860]
            end
            
            subgraph "Agent Tier"
                OrchContainer[Orchestrator Container<br/>orchestrator-agent<br/>Port: 8000]
                WhiteContainer[White Agent Container<br/>white-player-agent<br/>Port: 8001]
                BlackContainer[Black Agent Container<br/>black-player-agent<br/>Port: 8002]
            end
            
            subgraph "Engine Tier"
                MCPContainer[MCP Server Container<br/>mcp-chess-server<br/>Port: 8003]
            end
        end
        
        subgraph "Storage"
            Volume[Persistent Volume<br/>Game History & Sessions]
        end
        
        subgraph "Networking"
            LoadBalancer[Load Balancer]
            InternalNetwork[Internal Docker Network]
        end
    end
    
    LoadBalancer --> GradioContainer
    GradioContainer -.-> OrchContainer
    OrchContainer -.-> WhiteContainer
    OrchContainer -.-> BlackContainer
    WhiteContainer -.-> MCPContainer
    BlackContainer -.-> MCPContainer
    OrchContainer --> Volume
    
    InternalNetwork -.-> OrchContainer
    InternalNetwork -.-> WhiteContainer
    InternalNetwork -.-> BlackContainer
    InternalNetwork -.-> MCPContainer
```

### 6.2 Service Discovery and Communication

```mermaid
graph LR
    subgraph "Service Discovery"
        DNS[Docker DNS Resolution]
        ENV[Environment Variables]
    end
    
    subgraph "Service Endpoints"
        OrchEndpoint["orchestrator-agent:8000"]
        WhiteEndpoint["white-player-agent:8001"]
        BlackEndpoint["black-player-agent:8002"]
        MCPEndpoint["mcp-chess-server:8003"]
    end
    
    DNS --> OrchEndpoint
    DNS --> WhiteEndpoint
    DNS --> BlackEndpoint
    DNS --> MCPEndpoint
    
    ENV --> DNS
```

## 7. Technology Stack and Implementation Considerations

### 7.1 Core Libraries and Frameworks

| Component | Technology | Library/Framework | Version | Purpose |
|-----------|------------|-------------------|---------|---------|
| **Chess Logic** | Python | `python-chess` | ^1.999 | Board representation, move validation, PGN/FEN handling |
| **Chess Visualization** | Python | `chess.svg` | ^1.999 | SVG board generation |
| **Image Processing** | Python | `PIL`, `cairosvg` | ^10.0, ^2.7 | SVG to PNG conversion |
| **Agent Framework** | Python | `a2a-python` | ^0.1.0 | Agent-to-agent communication |
| **MCP Server** | Python | `fastmcp` | ^0.2.0 | Model Context Protocol implementation |
| **Chess Engine** | Binary | `stockfish` | ^15.0 | Move analysis and evaluation |
| **Web Interface** | Python | `gradio` | ^4.0 | Web application framework |
| **WebSocket** | Python | `websockets` | ^12.0 | Real-time communication |
| **HTTP Server** | Python | `fastapi` | ^0.104 | REST API endpoints |
| **Async Processing** | Python | `asyncio` | Built-in | Asynchronous operations |

### 7.2 Architecture Patterns

#### 7.2.1 Orchestrator Agent Pattern

```python
class OrchestratorAgent:
    """
    Stateful agent managing multiple concurrent games
    """
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}
        self.websocket_clients: Dict[str, WebSocket] = {}
        self.agent_clients = {
            'white': A2AClient('white-player-agent:8001'),
            'black': A2AClient('black-player-agent:8002')
        }
    
    async def handle_move_request(self, session_id: str):
        session = self.sessions[session_id]
        current_player = session.current_turn
        
        # Request move from appropriate agent
        move_response = await self.agent_clients[current_player].request_move(
            fen=session.current_fen,
            pgn=session.pgn_history
        )
        
        # Validate and apply move
        if self.validate_move(session, move_response.move):
            self.apply_move(session, move_response.move)
            await self.broadcast_game_state(session_id)
```

#### 7.2.2 Stateless Player Agent Pattern

```python
class PlayerAgent:
    """
    Stateless agent for move generation
    """
    def __init__(self, color: str):
        self.color = color
        self.mcp_client = MCPClient('mcp-chess-server:8003')
    
    async def generate_move(self, fen: str, pgn: str) -> Move:
        # Get best move from engine
        best_move = await self.mcp_client.call_tool(
            'get_best_move_given_history_in_pgn',
            {'pgn_history': pgn, 'depth': 15}
        )
        
        # Validate move
        is_valid = await self.mcp_client.call_tool(
            'is_move_valid_given_fen',
            {'fen': fen, 'move_uci': best_move.uci}
        )
        
        if is_valid:
            return best_move
        else:
            return await self.generate_fallback_move(fen)
```

### 7.3 Performance Considerations

#### 7.3.1 Concurrency Management

```mermaid
graph TB
    subgraph "Orchestrator Concurrency"
        SessionPool[Session Thread Pool<br/>Max: 100 concurrent games]
        WSPool[WebSocket Thread Pool<br/>Max: 500 connections]
        A2APool[A2A Communication Pool<br/>Max: 50 concurrent requests]
    end
    
    subgraph "Resource Management"
        MemoryCache[In-Memory Game Cache<br/>LRU Eviction]
        PersistentStorage[Persistent Game Storage<br/>SQLite/PostgreSQL]
        StockfishPool[Stockfish Process Pool<br/>Max: 10 engines]
    end
    
    SessionPool --> MemoryCache
    MemoryCache --> PersistentStorage
    A2APool --> StockfishPool
```

#### 7.3.2 Scalability Patterns

- **Horizontal Scaling**: Multiple orchestrator instances with session affinity
- **Caching Strategy**: Redis for session state and move caching
- **Database Sharding**: Session-based sharding for game history
- **Load Balancing**: Round-robin for player agents, sticky sessions for orchestrator

### 7.4 Error Handling and Resilience

#### 7.4.1 Fault Tolerance Mechanisms

```mermaid
stateDiagram-v2
    [*] --> Healthy
    Healthy --> Degraded: Partial Failure
    Healthy --> Failed: Critical Failure
    Degraded --> Healthy: Recovery
    Degraded --> Failed: Escalation
    Failed --> Recovery: Manual Intervention
    Recovery --> Healthy: Full Recovery
    
    state Healthy {
        [*] --> NormalOperation
        NormalOperation --> NormalOperation: All Services Available
    }
    
    state Degraded {
        [*] --> FallbackMode
        FallbackMode --> FallbackMode: Reduced Functionality
    }
    
    state Failed {
        [*] --> ServiceDown
        ServiceDown --> ServiceDown: Critical Services Unavailable
    }
```

#### 7.4.2 Error Recovery Strategies

| Error Type | Recovery Strategy | Timeout | Retry Policy |
|------------|------------------|---------|--------------|
| **Agent Communication** | Circuit breaker with exponential backoff | 30s | 3 retries, 2s base delay |
| **Chess Engine Timeout** | Fallback to simpler evaluation | 10s | No retry, immediate fallback |
| **WebSocket Disconnect** | Automatic reconnection with session restore | 5s | Infinite retries, 1s interval |
| **Database Connection** | Connection pooling with health checks | 15s | 5 retries, 1s delay |

## 8. Security Considerations

### 8.1 Authentication and Authorization

```mermaid
sequenceDiagram
    participant User as Web User
    participant WebApp as Gradio App
    participant Orch as Orchestrator
    participant Auth as Auth Service
    
    User->>WebApp: Access chess game
    WebApp->>Auth: Validate session
    Auth-->>WebApp: Session token
    WebApp->>Orch: WebSocket connect with token
    Orch->>Auth: Validate token
    Auth-->>Orch: User context
    Orch-->>WebApp: Connection established
```

### 8.2 Security Measures

- **Input Validation**: All chess moves validated against legal move generation
- **Session Security**: JWT tokens with expiration for WebSocket authentication
- **Rate Limiting**: Request throttling to prevent abuse
- **Container Security**: Minimal base images, non-root users, read-only filesystems
- **Network Security**: Internal container network isolation
- **Data Protection**: Encryption at rest for game history, TLS in transit

## 9. Monitoring and Observability

### 9.1 Metrics and Monitoring

```mermaid
graph TB
    subgraph "Application Metrics"
        GameMetrics[Game Metrics<br/>- Active games<br/>- Moves per minute<br/>- Game duration]
        AgentMetrics[Agent Metrics<br/>- Response times<br/>- Error rates<br/>- Engine accuracy]
        WebMetrics[Web Metrics<br/>- Connection count<br/>- Page load times<br/>- User sessions]
    end
    
    subgraph "Infrastructure Metrics"
        ContainerMetrics[Container Metrics<br/>- CPU/Memory usage<br/>- Network I/O<br/>- Disk usage]
        NetworkMetrics[Network Metrics<br/>- Latency<br/>- Throughput<br/>- Error rates]
    end
    
    subgraph "Monitoring Stack"
        Prometheus[Prometheus<br/>Metrics Collection]
        Grafana[Grafana<br/>Dashboards]
        AlertManager[AlertManager<br/>Notifications]
    end
    
    GameMetrics --> Prometheus
    AgentMetrics --> Prometheus
    WebMetrics --> Prometheus
    ContainerMetrics --> Prometheus
    NetworkMetrics --> Prometheus
    
    Prometheus --> Grafana
    Prometheus --> AlertManager
```

### 9.2 Logging Strategy

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "service": "orchestrator",
  "session_id": "abc123",
  "event": "move_processed",
  "details": {
    "move": "e2e4",
    "player": "white",
    "engine_time": 1.5,
    "evaluation": "+0.3"
  },
  "trace_id": "xyz789"
}
```

## 10. Testing Strategy

### 10.1 Test Architecture

```mermaid
graph TB
    subgraph "Test Pyramid"
        UnitTests[Unit Tests<br/>- Individual functions<br/>- Chess logic<br/>- Message parsing]
        IntegrationTests[Integration Tests<br/>- Agent communication<br/>- MCP tool calls<br/>- Database operations]
        E2ETests[End-to-End Tests<br/>- Complete game flows<br/>- WebSocket communication<br/>- User scenarios]
    end
    
    subgraph "Test Environment"
        TestContainers[Test Containers<br/>- Isolated environment<br/>- Mock services<br/>- Test data]
        MockServices[Mock Services<br/>- Stockfish simulator<br/>- WebSocket mock<br/>- Agent stubs]
    end
    
    UnitTests --> TestContainers
    IntegrationTests --> TestContainers
    E2ETests --> TestContainers
    TestContainers --> MockServices
```

### 10.2 Test Scenarios

#### Critical Path Tests
1. **Complete Game Flow**: Start → Moves → End → Result
2. **Session Management**: Create → Pause → Resume → Archive
3. **Error Recovery**: Network failures → Agent timeouts → Invalid moves
4. **Concurrent Games**: Multiple sessions → Resource isolation → Performance

#### Edge Case Tests
1. **Chess Rules**: En passant, castling, promotion, stalemate
2. **Time Controls**: Move timeouts, game timeouts, time increment
3. **Network Issues**: Disconnections, reconnections, partial failures
4. **Load Testing**: High concurrent users, memory pressure, CPU stress

## 11. Deployment and DevOps

### 11.1 CI/CD Pipeline

```mermaid
graph LR
    subgraph "Development"
        Code[Code Changes]
        Tests[Automated Tests]
        Build[Docker Build]
    end
    
    subgraph "Staging"
        Deploy[Deploy to Staging]
        IntegrationTest[Integration Tests]
        Performance[Performance Tests]
    end
    
    subgraph "Production"
        ProdDeploy[Deploy to Production]
        Monitor[Health Monitoring]
        Rollback[Automated Rollback]
    end
    
    Code --> Tests
    Tests --> Build
    Build --> Deploy
    Deploy --> IntegrationTest
    IntegrationTest --> Performance
    Performance --> ProdDeploy
    ProdDeploy --> Monitor
    Monitor --> Rollback
```

### 11.2 Configuration Management

```yaml
# docker-compose.yml
version: '3.8'
services:
  orchestrator:
    build: ./orchestrator
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@db:5432/chess
    depends_on:
      - redis
      - db
    networks:
      - chess-network

  white-agent:
    build: ./agents/white
    environment:
      - MCP_SERVER_URL=http://mcp-server:8003
    networks:
      - chess-network

  mcp-server:
    build: ./mcp-server
    volumes:
      - stockfish-engines:/opt/stockfish
    networks:
      - chess-network

networks:
  chess-network:
    driver: bridge
```

## 12. Future Enhancements and Extensibility

### 12.1 Planned Extensions

```mermaid
mindmap
  root((Chess System<br/>Extensions))
    AI Improvements
      Multi-Engine Support
      Machine Learning Models
      Opening Books
      Endgame Databases
    Game Features
      Tournament Mode
      Time Controls
      Analysis Mode
      Game Reviews
    Social Features
      User Accounts
      Rating System
      Game Sharing
      Spectator Mode
    Technical
      Real-time Streaming
      Mobile Apps
      API Gateway
      Microservices
```

### 12.2 Extensibility Points

1. **Player Agent Plugins**: Support for different AI engines and strategies
2. **Game Variants**: Chess960, King of the Hill, Three-Check
3. **Analysis Tools**: Position evaluation, move suggestions, game analysis
4. **Integration APIs**: External chess platforms, rating systems, databases

This technical design provides a comprehensive foundation for implementing the multi-agent chess system with clear architecture, well-defined interfaces, and robust implementation considerations.