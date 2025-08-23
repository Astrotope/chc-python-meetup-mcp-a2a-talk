# Python Stockfish Wrapper - Comprehensive Functionality Reference

## Overview
The Python stockfish library is a wrapper around the Stockfish chess engine, providing easy access to engine analysis, move validation, and position evaluation from Python.

## Installation and Setup

### Basic Setup
```python
from stockfish import Stockfish

# Initialize with default settings
stockfish = Stockfish()

# Initialize with custom path
stockfish = Stockfish(path="/usr/local/bin/stockfish")

# Initialize with parameters
stockfish = Stockfish(
    path="/usr/local/bin/stockfish",
    depth=15,
    parameters={
        "Debug Log File": "",
        "Contempt": 0,
        "Min Split Depth": 0,
        "Threads": 1,
        "Ponder": "false",
        "Hash": 16,
        "MultiPV": 1,
        "Skill Level": 20,
        "Move Overhead": 10,
        "Minimum Thinking Time": 20,
        "Slow Mover": 100,
        "UCI_Chess960": "false",
    }
)
```

## Core Functionality

### Position Management

#### Setting Board Position
```python
# Set position from FEN
stockfish.set_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

# Set from move list (UCI format)
stockfish.set_position(["e2e4", "e7e5", "g1f3"])

# Reset to starting position
stockfish.set_position([])
```

#### Getting Current Position
```python
# Get current FEN
fen = stockfish.get_fen_position()

# Get current board as 2D array
board_array = stockfish.get_board_visual()
print(board_array)
# Output: Visual representation of the board
```

### Move Operations

#### Getting Best Move
```python
# Get best move in current position
best_move = stockfish.get_best_move()  # Returns UCI format like "e2e4"

# Get best move with time limit
best_move = stockfish.get_best_move_time(1000)  # 1 second in milliseconds

# No best move available (game over)
if best_move is None:
    print("No legal moves or game is over")
```

#### Move Validation
```python
# Check if move is legal
is_valid = stockfish.is_move_correct("e2e4")  # Returns True/False

# Note: Move must be in UCI format (from_square + to_square + promotion)
```

#### Making Moves
```python
# Make a move (if legal)
success = stockfish.make_moves_from_current_position(["e2e4"])

# Make multiple moves
success = stockfish.make_moves_from_current_position(["e2e4", "e7e5", "g1f3"])
```

### Position Analysis

#### Position Evaluation
```python
# Get position evaluation in centipawns
evaluation = stockfish.get_evaluation()
# Returns: {"type": "cp", "value": 20} for centipawn evaluation
# Returns: {"type": "mate", "value": 3} for mate in 3
# Returns: None if position is invalid

# Check evaluation type
if evaluation["type"] == "cp":
    print(f"Position eval: {evaluation['value']} centipawns")
elif evaluation["type"] == "mate":
    print(f"Mate in {evaluation['value']} moves")
```

#### Top Moves Analysis
```python
# Get top N moves with evaluations
top_moves = stockfish.get_top_moves(3)  # Get top 3 moves
# Returns list of dictionaries:
# [
#   {"Move": "e2e4", "Centipawn": 20, "Mate": None},
#   {"Move": "d2d4", "Centipawn": 15, "Mate": None},
#   {"Move": "g1f3", "Centipawn": 10, "Mate": None}
# ]

for move_info in top_moves:
    move = move_info["Move"]
    cp = move_info["Centipawn"]
    mate = move_info["Mate"]
    
    if mate is not None:
        print(f"{move}: Mate in {mate}")
    else:
        print(f"{move}: {cp} centipawns")
```

### FEN and Position Validation

#### FEN Validation
```python
# Validate FEN string
is_valid = stockfish.is_fen_valid("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
# Returns: True/False

# Note: Validation "isn't perfect" according to docs
# May incorrectly handle some edge cases like checkmate positions
```

#### Position Checking
```python
# Check what piece is on a square
piece = stockfish.get_what_is_on_square("e4")  # Returns piece symbol or None
# Returns: "P" for white pawn, "p" for black pawn, None for empty

# Check if move will be a capture
capture_type = stockfish.will_move_be_a_capture("e4d5")
# Returns: Stockfish.Capture.DIRECT_CAPTURE, 
#          Stockfish.Capture.EN_PASSANT, or 
#          Stockfish.Capture.NO_CAPTURE
```

## Engine Configuration

### Parameter Management
```python
# Get current parameters
params = stockfish.get_parameters()

# Set individual parameter
stockfish.set_parameter("Hash", 512)  # Set hash table size
stockfish.set_parameter("Threads", 4)  # Set number of threads
stockfish.set_parameter("Skill Level", 15)  # Reduce engine strength

# Common parameters:
# - "Hash": Memory for hash table (MB)
# - "Threads": Number of CPU threads
# - "Skill Level": Engine strength (0-20, 20 = full strength)
# - "Depth": Search depth
# - "MultiPV": Number of principal variations
```

### Search Depth
```python
# Set search depth
stockfish.set_depth(18)

# Get current depth
depth = stockfish.get_depth()
```

## Advanced Features

### Wtime/Btime (Time Control)
```python
# Set time control for white and black
stockfish.set_wtime(300000)  # 5 minutes for white (milliseconds)
stockfish.set_btime(300000)  # 5 minutes for black (milliseconds)

# Get remaining time
white_time = stockfish.get_wtime()
black_time = stockfish.get_btime()
```

### Engine Information
```python
# Check if engine is running
is_running = stockfish.is_running()

# Get engine version/info (if available)
# Note: Method availability may vary by version
```

## Error Handling and Edge Cases

### Common Issues
```python
# Engine not found
try:
    stockfish = Stockfish(path="/wrong/path/stockfish")
except FileNotFoundError:
    print("Stockfish engine not found")

# Invalid position
stockfish.set_position("invalid fen")
evaluation = stockfish.get_evaluation()
if evaluation is None:
    print("Invalid position")

# No legal moves
best_move = stockfish.get_best_move()
if best_move is None:
    print("No legal moves (checkmate/stalemate)")

# Invalid move format
is_valid = stockfish.is_move_correct("invalid_move")  # Returns False
```

### FEN Validation Limitations
The library documentation notes that FEN validation "isn't perfect" and may:
- Incorrectly validate some invalid positions
- Have issues with checkmate position validation
- Miss some edge cases in position legality

## Integration Patterns

### MCP Tool Implementation
```python
def get_stockfish_move_logic(fen: str, time_limit: float = 2.0) -> Dict[str, Any]:
    """Get best move using Stockfish."""
    try:
        stockfish = Stockfish()
        stockfish.set_position(fen)
        
        # Set time limit (convert to milliseconds)
        best_move = stockfish.get_best_move_time(int(time_limit * 1000))
        
        return {
            "success": True,
            "move_uci": best_move,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "move_uci": None,
            "error": str(e)
        }

def validate_fen_logic(fen: str) -> Dict[str, Any]:
    """Validate FEN using Stockfish."""
    try:
        stockfish = Stockfish()
        is_valid = stockfish.is_fen_valid(fen)
        
        # Additional validation by trying to set position
        if is_valid:
            stockfish.set_position(fen)
            evaluation = stockfish.get_evaluation()
            # If evaluation is None, position might be invalid
            is_valid = evaluation is not None
        
        return {
            "valid": is_valid,
            "error": None
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }
```

### Analysis Pattern
```python
def analyze_position(fen: str, depth: int = 15) -> Dict[str, Any]:
    """Comprehensive position analysis."""
    try:
        stockfish = Stockfish(depth=depth)
        stockfish.set_position(fen)
        
        evaluation = stockfish.get_evaluation()
        best_move = stockfish.get_best_move()
        top_moves = stockfish.get_top_moves(5)
        
        return {
            "evaluation": evaluation,
            "best_move": best_move,
            "top_moves": top_moves,
            "fen": stockfish.get_fen_position()
        }
    except Exception as e:
        return {"error": str(e)}
```

## Performance Considerations

### Engine Initialization
- Creating Stockfish instances is expensive
- Reuse instances when possible
- Consider connection pooling for web applications

### Time Management
- `get_best_move()` uses engine's default time
- `get_best_move_time()` provides better control
- Longer times = better moves but slower response

### Memory Usage
- Hash parameter affects memory consumption
- Larger hash tables improve engine strength
- Default 16MB is minimal; consider 512MB+ for better play

## Comparison with python-chess Engine Interface

### Advantages of python-stockfish
- Simpler API for basic operations
- Direct FEN validation
- Built-in position evaluation
- Easy parameter configuration

### Advantages of python-chess + engine
- More flexible engine communication
- Support for multiple engines
- Async support
- Better integration with chess logic
- More comprehensive chess functionality

### When to Use Each
**Use python-stockfish when:**
- Simple engine analysis needed
- Working primarily with Stockfish
- Want straightforward API
- Don't need advanced chess operations

**Use python-chess + engine when:**
- Need full chess functionality
- Want to support multiple engines
- Require async operations
- Building comprehensive chess applications
- Need move generation, validation, notation parsing

## Version Compatibility Notes
- API may vary between versions
- Some methods might not be available in older versions
- Check documentation for your specific version
- Engine path and parameters may need adjustment per system

## Common Use Cases

### Move Validation Service
```python
def is_legal_move(fen: str, move_uci: str) -> bool:
    stockfish = Stockfish()
    stockfish.set_position(fen)
    return stockfish.is_move_correct(move_uci)
```

### Position Evaluation Service
```python
def evaluate_position(fen: str) -> float:
    stockfish = Stockfish()
    stockfish.set_position(fen)
    eval_dict = stockfish.get_evaluation()
    
    if eval_dict["type"] == "cp":
        return eval_dict["value"] / 100.0  # Convert to pawns
    elif eval_dict["type"] == "mate":
        return 999.9 if eval_dict["value"] > 0 else -999.9
    else:
        return 0.0
```

### Game Analysis
```python
def analyze_game(moves: List[str]) -> List[Dict]:
    stockfish = Stockfish()
    analysis = []
    
    for i, move in enumerate(moves):
        # Analyze position before move
        eval_before = stockfish.get_evaluation()
        best_move = stockfish.get_best_move()
        
        # Make the move
        stockfish.make_moves_from_current_position([move])
        
        analysis.append({
            "move_number": i + 1,
            "move": move,
            "evaluation_before": eval_before,
            "best_move": best_move,
            "was_best": move == best_move
        })
    
    return analysis
```

This comprehensive reference covers the full functionality of the python-stockfish wrapper for integrating Stockfish chess engine analysis into Python applications.