#!/usr/bin/env python3
"""
Chess Game Manager - Comprehensive chess board management with game state tracking
"""

import chess
import chess.pgn
import json
from typing import List, Dict, Any, Optional
from google.adk.tools.tool_context import ToolContext


class ChessGameManager:
    """Comprehensive chess board management with game state tracking"""
    
    _instances = {}  # browser_id -> ChessGameManager instance
    
    def __new__(cls, browser_id: str = None):
        if browser_id is None:
            # Fallback for direct instantiation (legacy)
            return super().__new__(cls)
        
        if browser_id not in cls._instances:
            cls._instances[browser_id] = super().__new__(cls)
        return cls._instances[browser_id]
    
    def __init__(self, browser_id: str = None):
        if not hasattr(self, '_initialized'):
            self.board = chess.Board()
            self._move_history = []
            self._game_metadata = {
                "start_time": None,
                "end_time": None,
                "result": None
            }
            self._initialized = True
    
    @classmethod
    def get_for_browser(cls, browser_id: str):
        """Get ChessGameManager instance for specific browser session"""
        return cls(browser_id)
    
    def reset_game(self):
        """Reset the game to starting position"""
        self.board = chess.Board()
        self._move_history = []
        self._game_metadata = {
            "start_time": None,
            "end_time": None,
            "result": None
        }
    
    def make_move(self, uci: str) -> bool:
        """Apply UCI move to board. Returns True if successful."""
        try:
            move = chess.Move.from_uci(uci)
            if move in self.board.legal_moves:
                self.board.push(move)
                self._move_history.append(uci)
                return True
            return False
        except:
            return False
    
    def get_fen(self) -> str:
        """Return current board position as FEN string."""
        return self.board.fen()
    
    def is_legal_move(self, uci: str) -> bool:
        """Check if UCI move is legal in current position."""
        try:
            move = chess.Move.from_uci(uci)
            return move in self.board.legal_moves
        except:
            return False
    
    def get_legal_moves(self) -> List[str]:
        """Return list of all legal moves in UCI format."""
        return [move.uci() for move in self.board.legal_moves]
    
    def is_gameover(self) -> bool:
        """Check if game has ended."""
        return self.board.is_game_over()
    
    def end_reason(self) -> str:
        """Return reason for game end."""
        if not self.board.is_game_over():
            return "game_active"
        elif self.board.is_checkmate():
            winner = "black" if self.board.turn else "white"
            return f"checkmate_{winner}_wins"
        elif self.board.is_stalemate():
            return "stalemate_draw"
        elif self.board.is_insufficient_material():
            return "insufficient_material_draw"
        elif self.board.is_seventyfive_moves():
            return "75_move_rule_draw"
        elif self.board.is_fivefold_repetition():
            return "repetition_draw"
        else:
            return "draw"
    
    def move_history(self) -> List[str]:
        """Return list of all moves in UCI notation."""
        return self._move_history.copy()
    
    def move_history_san(self) -> List[str]:
        """Return move history in Standard Algebraic Notation (SAN)."""
        temp_board = chess.Board()
        san_moves = []
        for uci_move in self._move_history:
            move = chess.Move.from_uci(uci_move)
            san_moves.append(temp_board.san(move))
            temp_board.push(move)
        return san_moves
    
    def current_turn(self) -> str:
        """Return current player: 'white' or 'black'."""
        return "white" if self.board.turn else "black"
    
    def reset_game(self) -> None:
        """Reset board to initial position."""
        self.board.reset()
        self._move_history.clear()
        self._game_metadata = {
            "start_time": None,
            "end_time": None,
            "result": None
        }
    
    def get_game_summary(self) -> Dict[str, Any]:
        """Return comprehensive game state summary."""
        return {
            "fen": self.get_fen(),
            "turn": self.current_turn(),
            "move_count": len(self._move_history),
            "moves_uci": self.move_history(),
            "moves_san": self.move_history_san(),
            "legal_moves": self.get_legal_moves(),
            "game_over": self.is_gameover(),
            "end_reason": self.end_reason() if self.is_gameover() else None,
            "in_check": self.board.is_check(),
            "metadata": self._game_metadata
        }
    
    def to_pgn(self) -> str:
        """Export game as PGN format."""
        game = chess.pgn.Game()
        game.headers["Event"] = "ADK Chess Game"
        game.headers["Result"] = self.end_reason() if self.is_gameover() else "*"
        
        node = game
        temp_board = chess.Board()
        
        for uci_move in self._move_history:
            move = chess.Move.from_uci(uci_move)
            node = node.add_variation(move)
            temp_board.push(move)
        
        return str(game)
    
    def load_from_fen(self, fen: str) -> bool:
        """Load game state from FEN string."""
        try:
            self.board = chess.Board(fen)
            self._move_history.clear()  # Clear history when loading from FEN
            return True
        except:
            return False
    
    def serialize(self) -> str:
        """Serialize game manager state to JSON string for storage."""
        state = {
            "fen": self.get_fen(),
            "move_history": self._move_history,
            "metadata": self._game_metadata
        }
        return json.dumps(state)
    
    @classmethod
    def deserialize(cls, state_json: str) -> 'ChessGameManager':
        """Deserialize game manager from JSON string."""
        state = json.loads(state_json)
        manager = cls()
        manager.load_from_fen(state["fen"])
        manager._move_history = state.get("move_history", [])
        manager._game_metadata = state.get("metadata", {})
        return manager


# Game Management Tools with Planning Guidance

def start_game(tool_context: ToolContext) -> str:
    """Initialize a new chess game.
    
    Planning considerations:
    - Reset board to starting position (standard FEN)
    - Set current turn to white
    - Clear move history
    - Update session state with fresh game manager
    """
    print(f"🚀 ORCHESTRATOR CALLED: start_game()")
    browser_id = tool_context.state.get("browser_session_id")
    
    if browser_id:
        game_manager = ChessGameManager.get_for_browser(browser_id)
    else:
        game_manager = ChessGameManager()
    
    game_manager.reset_game()
    
    # Store serialized game manager in session state
    tool_context.state["chess_game_manager"] = game_manager.serialize()
    tool_context.state["game_active"] = True
    tool_context.state["planning_context"] = "game_started"
    
    final_fen = game_manager.get_fen()
    return f"New chess game started. FEN: {final_fen}. White to move."


def play_turn(tool_context: ToolContext) -> str:
    """Execute one complete turn: get move from current player, validate, apply.
    
    Planning considerations:
    - Determine whose turn it is
    - Call appropriate sub-agent (white_player or black_player)
    - Validate returned move is legal
    - Apply move if valid, or request retry if invalid
    - Check if game has ended after move
    - Update session state
    """
    browser_id = tool_context.state.get("browser_session_id")
    if not browser_id:
        return "No browser session ID. Cannot access game."
    
    game_manager = ChessGameManager.get_for_browser(browser_id)
    
    if game_manager.is_gameover():
        reason = game_manager.end_reason()
        tool_context.state["game_active"] = False
        tool_context.state["planning_context"] = "game_ended"
        return f"Game already ended: {reason}"
    
    current_player = game_manager.current_turn()
    current_fen = game_manager.get_fen()
    legal_moves_count = len(game_manager.get_legal_moves())
    
    # Update planning context for sub-agent coordination
    tool_context.state["planning_context"] = f"awaiting_{current_player}_move"
    tool_context.state["current_fen"] = current_fen
    tool_context.state["legal_moves_count"] = legal_moves_count
    
    return f"Turn for {current_player}. Current FEN: {current_fen}. Legal moves: {legal_moves_count}. Move count: {len(game_manager.move_history())}"


def apply_move(tool_context: ToolContext, uci_move: str) -> str:
    """Apply a specific UCI move to the current game.
    
    Planning considerations:
    - Validate move is legal in current position
    - Apply move and update game state
    - Check for game end conditions
    - Update session state with new position
    """
    print(f"♟️ ORCHESTRATOR CALLED: apply_move(uci_move='{uci_move}')")
    browser_id = tool_context.state.get("browser_session_id")
    if not browser_id:
        return "No browser session ID. Cannot access game."
    
    game_manager = ChessGameManager.get_for_browser(browser_id)
    
    if game_manager.is_gameover():
        return f"Game already ended: {game_manager.end_reason()}"
    
    if not game_manager.is_legal_move(uci_move):
        legal_moves = game_manager.get_legal_moves()
        return f"Illegal move: {uci_move}. Legal moves: {legal_moves[:10]}{'...' if len(legal_moves) > 10 else ''}"
    
    # Apply the move
    success = game_manager.make_move(uci_move)
    if not success:
        return f"Failed to apply move: {uci_move}"
    
    # Update session state
    tool_context.state["last_move"] = uci_move
    
    # Check game status
    if game_manager.is_gameover():
        reason = game_manager.end_reason()
        tool_context.state["game_active"] = False
        tool_context.state["planning_context"] = "game_ended"
        return f"Move {uci_move} applied. Game ended: {reason}. Final FEN: {game_manager.get_fen()}"
    else:
        next_player = game_manager.current_turn()
        tool_context.state["planning_context"] = f"move_applied_next_{next_player}"
        return f"Move {uci_move} applied successfully. Next turn: {next_player}. FEN: {game_manager.get_fen()}"


def get_game_status(tool_context: ToolContext) -> str:
    """Return current game state for monitoring.
    
    Planning considerations:
    - Provide comprehensive game information
    - Include current position, turn, move history
    - Report game end status if applicable
    """
    print(f"📊 ORCHESTRATOR CALLED: get_game_status()")
    browser_id = tool_context.state.get("browser_session_id")
    if not browser_id:
        return "No browser session ID. Cannot access game."
    
    game_manager = ChessGameManager.get_for_browser(browser_id)
    summary = game_manager.get_game_summary()
    
    return f"Game Status: FEN={summary['fen']}, Turn={summary['turn']}, Moves={summary['move_count']}, GameOver={summary['game_over']}, Reason={summary['end_reason']}"


def reset_game(tool_context: ToolContext) -> str:
    """Reset current game to initial position.
    
    Planning considerations:
    - Clear all game state
    - Reset to starting position
    - Update session state
    """
    browser_id = tool_context.state.get("browser_session_id")
    if not browser_id:
        return "No browser session ID. Cannot access game."
    
    game_manager = ChessGameManager.get_for_browser(browser_id)
    game_manager.reset_game()
    tool_context.state["game_active"] = True
    tool_context.state["planning_context"] = "game_reset"
    
    return f"Game reset to initial position. FEN: {game_manager.get_fen()}. White to move."