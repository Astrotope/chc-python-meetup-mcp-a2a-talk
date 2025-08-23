# Chess Core Mechanics Analysis

## Overview
Analysis of [alipala/multiagent_llm_chess](https://github.com/alipala/multiagent_llm_chess) focusing on core chess functionality useful for our MCP tools and agent system.

## Board State Management

### Core State Representation
```python
import chess

# Primary board state
board = chess.Board()

# Key state access methods
board.fen()                    # Position in FEN notation
board.turn                     # Current player (chess.WHITE/BLACK)  
board.fullmove_number          # Move number
board.halfmove_clock           # Moves since capture/pawn advance
board.legal_moves              # All legal moves from position
```

### State Persistence
- **FEN notation**: Complete position representation
- **Move stack**: Built-in history via `board.move_stack`
- **Automatic handling**: Castling rights, en passant, etc.

## End of Game Detection

### Built-in Detection Methods
```python
# Core termination conditions
board.is_checkmate()           # Checkmate
board.is_stalemate()          # Stalemate  
board.is_insufficient_material() # Draw - insufficient material
board.is_seventyfive_moves()   # 75-move rule
board.is_fivefold_repetition() # Repetition draw
board.is_check()              # Check detection

# Game outcome
outcome = board.outcome()      # Returns Outcome object if game over
if outcome:
    outcome.winner             # chess.WHITE, chess.BLACK, or None (draw)
    outcome.termination        # Termination reason enum
```

### MCP Tool Implementation
```python
async def check_game_status(fen: str) -> Dict:
    board = chess.Board(fen)
    outcome = board.outcome()
    
    return {
        "is_game_over": outcome is not None,
        "winner": str(outcome.winner) if outcome and outcome.winner else None,
        "termination": str(outcome.termination) if outcome else None,
        "is_check": board.is_check(),
        "is_checkmate": board.is_checkmate(),
        "is_stalemate": board.is_stalemate()
    }
```

## Move Validation and Application

### Core Move Operations
```python
# Move validation
move = chess.Move.from_uci("e2e4")
is_legal = move in board.legal_moves

# Move application
if is_legal:
    board.push(move)           # Apply move
    new_fen = board.fen()      # Get resulting position

# Undo moves
board.pop()                    # Undo last move
```

### Legal Move Generation
```python
# Get all legal moves
legal_moves = list(board.legal_moves)
legal_uci = [move.uci() for move in legal_moves]

# Check specific move
def is_move_valid(board, move_uci):
    try:
        move = chess.Move.from_uci(move_uci)
        return move in board.legal_moves
    except ValueError:
        return False
```

## Essential MCP Tools

### 1. Move Validation Tools
```python
async def is_move_valid_given_fen(fen: str, move_uci: str) -> bool:
    """Validate if move is legal in given position"""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        return move in board.legal_moves
    except (ValueError, chess.InvalidFenError):
        return False

async def get_legal_moves(fen: str) -> List[str]:
    """Get all legal moves from position"""
    try:
        board = chess.Board(fen)
        return [move.uci() for move in board.legal_moves]
    except chess.InvalidFenError:
        return []
```

### 2. Board State Tools
```python
async def apply_move(fen: str, move_uci: str) -> Dict:
    """Apply move and return new position"""
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        
        if move not in board.legal_moves:
            return {"success": False, "error": "Illegal move"}
        
        board.push(move)
        return {
            "success": True,
            "new_fen": board.fen(),
            "is_check": board.is_check(),
            "move_number": board.fullmove_number
        }
    except (ValueError, chess.InvalidFenError) as e:
        return {"success": False, "error": str(e)}

async def get_position_info(fen: str) -> Dict:
    """Get comprehensive position information"""
    try:
        board = chess.Board(fen)
        return {
            "turn": "white" if board.turn == chess.WHITE else "black",
            "move_number": board.fullmove_number,
            "halfmove_clock": board.halfmove_clock,
            "is_check": board.is_check(),
            "legal_move_count": len(list(board.legal_moves)),
            "can_castle_kingside": board.has_kingside_castling_rights(board.turn),
            "can_castle_queenside": board.has_queenside_castling_rights(board.turn)
        }
    except chess.InvalidFenError:
        return {"error": "Invalid FEN"}
```

### 3. Game History Tools
```python
async def get_position_from_moves(moves: List[str]) -> str:
    """Get FEN from sequence of moves"""
    board = chess.Board()
    
    for move_uci in moves:
        try:
            move = chess.Move.from_uci(move_uci)
            if move in board.legal_moves:
                board.push(move)
            else:
                return None  # Invalid sequence
        except ValueError:
            return None
    
    return board.fen()

async def validate_move_sequence(moves: List[str]) -> bool:
    """Validate entire move sequence"""
    board = chess.Board()
    
    for move_uci in moves:
        try:
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                return False
            board.push(move)
        except ValueError:
            return False
    
    return True
```

## Integration with Stockfish

### Engine Analysis Tools
```python
import chess.engine

async def get_best_move_stockfish(fen: str, depth: int = 15) -> Dict:
    """Get Stockfish's best move for position"""
    try:
        board = chess.Board(fen)
        
        with chess.engine.SimpleEngine.popen_uci("stockfish") as engine:
            result = engine.play(board, chess.engine.Limit(depth=depth))
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            
            return {
                "best_move": result.move.uci(),
                "evaluation": info["score"].relative.score(),
                "depth": info.get("depth", depth),
                "nodes": info.get("nodes", 0)
            }
    except Exception as e:
        return {"error": str(e)}

async def evaluate_position(fen: str, depth: int = 15) -> float:
    """Get position evaluation from Stockfish"""
    try:
        board = chess.Board(fen)
        
        with chess.engine.SimpleEngine.popen_uci("stockfish") as engine:
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            score = info["score"].relative.score()
            
            # Convert to centipawns or mate score
            if score is not None:
                return score / 100.0  # Convert to pawn units
            else:
                # Handle mate scores
                mate = info["score"].relative.mate()
                return 999.0 if mate > 0 else -999.0
                
    except Exception:
        return 0.0
```

## Error Handling Patterns

### Robust FEN Validation
```python
def safe_board_from_fen(fen: str) -> Optional[chess.Board]:
    """Safely create board from FEN"""
    try:
        board = chess.Board(fen)
        # Additional validation
        if not board.is_valid():
            return None
        return board
    except (chess.InvalidFenError, ValueError):
        return None
```

### Move Validation Pipeline
```python
def validate_and_apply_move(fen: str, move_uci: str) -> Dict:
    """Complete move validation and application"""
    # Step 1: Validate FEN
    board = safe_board_from_fen(fen)
    if not board:
        return {"success": False, "error": "Invalid FEN"}
    
    # Step 2: Parse move
    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError:
        return {"success": False, "error": "Invalid move format"}
    
    # Step 3: Check legality
    if move not in board.legal_moves:
        return {"success": False, "error": "Illegal move"}
    
    # Step 4: Apply move
    board.push(move)
    
    return {
        "success": True,
        "new_fen": board.fen(),
        "san_notation": board.san(move),
        "is_capture": board.is_capture(move),
        "is_check": board.is_check()
    }
```

## Recommended MCP Tool Set

Based on the analysis, implement these core MCP tools:

1. **is_move_valid_given_fen** - Basic move validation
2. **get_legal_moves** - All legal moves from position  
3. **apply_move** - Apply move and get new position
4. **check_game_status** - Comprehensive game end detection
5. **get_position_info** - Position metadata and state
6. **get_best_move_stockfish** - Engine move recommendation
7. **evaluate_position** - Position evaluation score
8. **validate_move_sequence** - Validate move history

These tools provide complete chess functionality for our multi-agent system without unnecessary complexity.