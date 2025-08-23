# Python Chess Library - Comprehensive Functionality Reference

## Overview
Python-chess is a comprehensive chess library for Python providing move generation, validation, PGN parsing, engine communication, and tablebase probing.

## Core Classes and Objects

### chess.Board
The main board representation class with full game state management.

#### Initialization
```python
import chess

# Standard starting position
board = chess.Board()

# From FEN string
board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

# Chess960 variant
board = chess.Board(chess960=True)
```

#### Board State Properties
- `board.turn` - Current player (True=White, False=Black)
- `board.fullmove_number` - Full move counter
- `board.halfmove_clock` - Halfmove clock for 50-move rule
- `board.castling_rights` - Castling availability
- `board.ep_square` - En passant target square
- `board.fen()` - Get FEN representation
- `board.copy()` - Create board copy

#### Game Status Checking
- `board.is_checkmate()` - Check if position is checkmate
- `board.is_stalemate()` - Check if position is stalemate
- `board.is_check()` - Check if king is in check
- `board.is_game_over()` - Check if game has ended
- `board.outcome()` - Get game outcome with termination reason
- `board.is_insufficient_material()` - Check for insufficient material
- `board.is_seventyfive_moves()` - Check 75-move rule
- `board.is_fivefold_repetition()` - Check 5-fold repetition

#### Move Generation and Validation
```python
# Get all legal moves
legal_moves = board.legal_moves  # LegalMoveGenerator object
legal_moves_list = list(board.legal_moves)

# Check if specific move is legal
move = chess.Move.from_uci("e2e4")
is_legal = move in board.legal_moves

# Generate moves for specific pieces/squares
attacks = board.attacks(square)  # Squares attacked from given square
attackers = board.attackers(color, square)  # Pieces attacking square
```

#### Making and Unmaking Moves
```python
# Make a move
move = chess.Move.from_uci("e2e4")
board.push(move)

# Make move from SAN
move = board.push_san("e4")  # Returns Move object

# Unmake last move
board.pop()  # Returns the undone Move

# Move validation before pushing
if move in board.legal_moves:
    board.push(move)
```

#### Piece Access and Manipulation
```python
# Get piece at square
piece = board.piece_at(chess.E4)  # Returns Piece object or None

# Set piece at square (use carefully)
board.set_piece_at(chess.E4, chess.Piece(chess.PAWN, chess.WHITE))

# Remove piece
board.remove_piece_at(chess.E4)

# Get piece map
piece_map = board.piece_map()  # Dict of {square: Piece}
```

### chess.Move
Represents a chess move with from/to squares and optional promotion.

#### Creation
```python
# From UCI notation
move = chess.Move.from_uci("e2e4")
move = chess.Move.from_uci("e7e8q")  # Promotion to queen

# Direct construction
move = chess.Move(chess.E2, chess.E4)
move = chess.Move(chess.E7, chess.E8, promotion=chess.QUEEN)
```

#### Properties
- `move.from_square` - Starting square
- `move.to_square` - Ending square  
- `move.promotion` - Promoted piece type (or None)
- `move.uci()` - UCI string representation

### chess.Piece
Represents a chess piece with type and color.

#### Creation and Properties
```python
# Create pieces
white_pawn = chess.Piece(chess.PAWN, chess.WHITE)
black_king = chess.Piece(chess.KING, chess.BLACK)

# Properties
piece.piece_type  # PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
piece.color       # True (WHITE) or False (BLACK)
piece.symbol()    # Character representation ('P', 'p', 'N', 'n', etc.)
```

#### Piece Type Constants
```python
chess.PAWN = 1
chess.KNIGHT = 2  
chess.BISHOP = 3
chess.ROOK = 4
chess.QUEEN = 5
chess.KING = 6
```

## Square and File/Rank Operations

### Square Constants and Functions
```python
# Square constants (0-63)
chess.A1, chess.B1, ..., chess.H8

# Square name conversion
square_name = chess.square_name(chess.E4)  # "e4"
square_index = chess.parse_square("e4")    # 28

# File and rank functions
file_index = chess.square_file(chess.E4)   # 4 (0-7)
rank_index = chess.square_rank(chess.E4)   # 3 (0-7)

# Distance calculations
distance = chess.square_distance(chess.A1, chess.H8)
manhattan = chess.square_manhattan_distance(chess.A1, chess.H8)
knight_dist = chess.square_knight_distance(chess.A1, chess.H8)

# Square manipulation
mirrored = chess.square_mirror(chess.E4)   # Mirror vertically
```

## Notation Parsing and Generation

### Standard Algebraic Notation (SAN)
```python
# Parse SAN to move
move = board.parse_san("Nf3")
move = board.parse_san("O-O")      # Castling
move = board.parse_san("exd5")     # Capture
move = board.parse_san("e8=Q+")    # Promotion with check

# Convert move to SAN
san_string = board.san(move)

# Variation to SAN
moves = [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")]
variation = board.variation_san(moves)  # "1. e4 e5"
```

### UCI Notation
```python
# UCI format: from_square + to_square + promotion
"e2e4"    # Pawn move
"g1f3"    # Knight move  
"e7e8q"   # Promotion to queen
"e1g1"    # Castling (king move)
```

### FEN (Forsyth-Edwards Notation)
```python
# Get FEN string
fen = board.fen()

# Set position from FEN
board.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

# Starting position constant
chess.STARTING_FEN
```

### EPD (Extended Position Description)
```python
# Get EPD with opcodes
epd = board.epd(bm=chess.Move.from_uci("e2e4"))  # Best move opcode

# Set from EPD
board.set_epd("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm e2e4;")
```

## Engine Communication

### UCI Engine Interface
```python
import chess.engine

# Start engine (synchronous)
engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")

# Start engine (asynchronous)
transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

# Get best move
board = chess.Board()
result = engine.play(board, chess.engine.Limit(time=1.0))
best_move = result.move

# Analysis
info = engine.analyse(board, chess.engine.Limit(depth=15))
score = info["score"]
pv = info["pv"]  # Principal variation

# Configure engine options
engine.configure({"Hash": 512, "Threads": 4})

# Quit engine
engine.quit()
```

### XBoard Engine Interface
```python
# Start XBoard engine
engine = chess.engine.SimpleEngine.popen_xboard("/path/to/xboard/engine")
```

### Engine Limits
```python
# Time limits
limit = chess.engine.Limit(time=2.0)           # 2 seconds
limit = chess.engine.Limit(depth=15)           # 15 ply
limit = chess.engine.Limit(nodes=1000000)      # 1M nodes
limit = chess.engine.Limit(mate=3)             # Find mate in 3
limit = chess.engine.Limit(white_clock=300.0, white_inc=5.0)  # Time control
```

## PGN (Portable Game Notation)

### Reading PGN Files
```python
import chess.pgn

# Read single game
with open("game.pgn") as pgn_file:
    game = chess.pgn.read_game(pgn_file)

# Read multiple games
with open("games.pgn") as pgn_file:
    while True:
        game = chess.pgn.read_game(pgn_file)
        if game is None:
            break
        # Process game
```

### Creating PGN Games
```python
# Create new game
game = chess.pgn.Game()

# Set headers
game.headers["Event"] = "World Championship"
game.headers["White"] = "Kasparov"
game.headers["Black"] = "Deep Blue"
game.headers["Result"] = "0-1"

# Add moves
node = game.add_variation(chess.Move.from_uci("e2e4"))
node = node.add_variation(chess.Move.from_uci("e7e5"))

# Add comments and annotations
node.comment = "Excellent opening choice"
node.nags.add(chess.pgn.NAG_GOOD_MOVE)
```

### PGN Visitors
```python
# Custom visitor for processing
class MyVisitor(chess.pgn.BaseVisitor):
    def visit_move(self, board, move):
        # Process each move
        pass
    
    def visit_comment(self, comment):
        # Process comments
        pass

# Use visitor
with open("game.pgn") as pgn_file:
    visitor = MyVisitor()
    game = chess.pgn.read_game(pgn_file, visitor=visitor)
```

## Opening Books

### Polyglot Opening Books
```python
import chess.polyglot

# Open book
book = chess.polyglot.open_reader("book.bin")

# Find entries for position
board = chess.Board()
entries = list(book.find_all(board))

# Get weighted random move
entry = book.weighted_choice(board)
if entry:
    move = entry.move
    weight = entry.weight

book.close()
```

## Endgame Tablebases

### Syzygy Tablebases
```python
import chess.syzygy

# Open tablebase
tablebase = chess.syzygy.open_tablebase("/path/to/syzygy")

# Probe for best move
board = chess.Board("8/8/8/8/8/8/7k/R6K w - - 0 1")
try:
    move = tablebase.get_best_move(board)
    wdl = tablebase.probe_wdl(board)  # Win/Draw/Loss
    dtz = tablebase.probe_dtz(board)  # Distance to zero
except chess.syzygy.MissingTableError:
    # Tablebase not available for this position
    pass

tablebase.close()
```

### Gaviota Tablebases
```python
import chess.gaviota

# Open tablebase
tablebase = chess.gaviota.open_tablebase("/path/to/gaviota")

# Probe position
board = chess.Board("8/8/8/8/8/8/7k/R6K w - - 0 1")
try:
    dtm = tablebase.probe_dtm(board)  # Distance to mate
    wdl = tablebase.probe_wdl(board)
except chess.gaviota.MissingTableError:
    pass

tablebase.close()
```

## Chess Variants

### Supported Variants
```python
import chess.variant

# Standard variants
board = chess.variant.KingOfTheHillBoard()
board = chess.variant.ThreeCheckBoard()  
board = chess.variant.AtomicBoard()
board = chess.variant.GiveawayBoard()
board = chess.variant.AntichessBoard()
board = chess.variant.SuicideBoard()
board = chess.variant.RacingKingsBoard()
board = chess.variant.HordeBoard()
board = chess.variant.CrazyhouseBoard()

# Chess960
board = chess.Board(chess960=True)
```

### Variant Information
```python
# Get variant details
board.uci_variant      # UCI identifier
board.xboard_variant   # XBoard identifier  
board.starting_fen     # Starting position FEN
```

## SVG Board Rendering

### Basic Rendering
```python
import chess.svg

board = chess.Board()

# Render board as SVG
svg = chess.svg.board(board=board)

# Highlight squares
svg = chess.svg.board(
    board=board,
    squares=chess.SquareSet([chess.E2, chess.E4])  # Highlight squares
)

# Show arrows
svg = chess.svg.board(
    board=board,
    arrows=[chess.svg.Arrow(chess.E2, chess.E4)]   # Move arrow
)
```

## Utility Functions

### Piece and Square Utilities
```python
# Piece symbols and names
chess.piece_symbol(chess.QUEEN)  # 'q'
chess.piece_name(chess.QUEEN)    # 'queen'

# Color names
chess.COLOR_NAMES[chess.WHITE]   # 'white'
chess.COLOR_NAMES[chess.BLACK]   # 'black'

# File and rank names
chess.FILE_NAMES[chess.FILE_E]   # 'e'
chess.RANK_NAMES[chess.RANK_4]   # '4'
```

### Square Sets
```python
# Create square sets
squares = chess.SquareSet([chess.E4, chess.D4, chess.F4])
squares = chess.SquareSet(chess.BB_RANK_4)  # Entire 4th rank

# Operations
squares.add(chess.E5)
squares.remove(chess.E4)
squares.clear()

# Bitboard operations
bb = squares.mask  # Get underlying bitboard
```

## Error Handling

### Common Exceptions
```python
try:
    board = chess.Board("invalid fen")
except ValueError as e:
    # Invalid FEN format
    pass

try:
    move = chess.Move.from_uci("invalid")
except ValueError as e:
    # Invalid UCI format
    pass

try:
    move = board.parse_san("invalid")
except ValueError as e:
    # Invalid SAN notation
    pass
```

## Performance Considerations

### Legal Move Generation
- `board.legal_moves` is a generator - iterate once or convert to list
- Use `move in board.legal_moves` for single move validation
- For multiple validations, generate list once: `legal_list = list(board.legal_moves)`

### Board Copying
- `board.copy()` creates deep copy - expensive for frequent use
- Consider push/pop pattern for temporary moves
- Stack operations are faster than copying

### Memory Management
- Close engines, tablebases, and opening books when done
- Use context managers or try/finally for cleanup
- Large PGN files: use streaming with visitors instead of loading all games

## Integration Patterns

### MCP Tool Implementation Pattern
```python
def chess_tool_logic(fen: str, *args) -> Dict[str, Any]:
    """Standard pattern for chess MCP tools."""
    try:
        board = chess.Board(fen)
        # Perform chess operations
        result = perform_operation(board, *args)
        return {
            "success": True,
            "result": result,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": str(e)
        }
```

### Engine Communication Pattern
```python
async def engine_analysis(fen: str) -> Dict[str, Any]:
    """Pattern for engine communication."""
    transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")
    try:
        board = chess.Board(fen)
        info = await engine.analyse(board, chess.engine.Limit(time=1.0))
        return {"score": info["score"], "pv": info["pv"]}
    finally:
        await engine.quit()
```

## Constants Reference

### Standard FEN Strings
- `chess.STARTING_FEN` - Standard starting position
- `chess.STARTING_BOARD_FEN` - Board part of starting FEN

### Piece Type Values
- `chess.PAWN = 1`
- `chess.KNIGHT = 2`
- `chess.BISHOP = 3` 
- `chess.ROOK = 4`
- `chess.QUEEN = 5`
- `chess.KING = 6`

### Color Values
- `chess.WHITE = True`
- `chess.BLACK = False`

### File and Rank Constants
- Files: `chess.FILE_A` through `chess.FILE_H` (0-7)
- Ranks: `chess.RANK_1` through `chess.RANK_8` (0-7)

This comprehensive reference covers the full functionality of the python-chess library for implementing chess-related applications and MCP tools.