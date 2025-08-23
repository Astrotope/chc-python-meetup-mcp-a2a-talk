"""
Integration tests for chess MCP server tools.

Tests the actual MCP tool endpoints through direct function calls.
"""
import pytest
from chess_mcp_server import (
    validate_fen_logic,
    validate_move_logic,
    make_move_logic,
    get_legal_moves_logic,
    get_game_status_logic,
    get_stockfish_move_logic,
    health_check_logic
)


class TestMCPToolIntegration:
    """Test MCP tool integration through direct function calls."""
    
    def test_validate_fen_tool(self):
        """Test validate_fen logic function."""
        # Test valid FEN
        result = validate_fen_logic("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        assert result["valid"] is True
        assert result["error"] is None
        
        # Test invalid FEN
        result = validate_fen_logic("invalid_fen")
        assert result["valid"] is False
        assert result["error"] is not None
    
    def test_validate_move_tool(self):
        """Test validate_move logic function."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Test valid move
        result = validate_move_logic(fen, "e2e4")
        assert result["valid"] is True
        
        # Test invalid move
        result = validate_move_logic(fen, "e2e5")
        assert result["valid"] is False
    
    def test_make_move_tool(self):
        """Test make_move logic function."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        result = make_move_logic(fen, "e2e4")
        assert result["success"] is True
        assert result["new_fen"] != fen
        assert " b " in result["new_fen"]  # Should be Black's turn
    
    def test_get_legal_moves_tool(self):
        """Test get_legal_moves logic function."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        result = get_legal_moves_logic(fen)
        assert result["success"] is True
        assert result["count"] == 20
        assert "e2e4" in result["legal_moves"]
        assert "g1f3" in result["legal_moves"]
    
    def test_get_game_status_tool(self):
        """Test get_game_status logic function."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        result = get_game_status_logic(fen)
        assert result["is_game_over"] is False
        assert result["current_turn"] == "white"
        assert result["legal_moves_count"] == 20
    
    def test_get_stockfish_move_tool(self):
        """Test get_stockfish_move logic function."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        result = get_stockfish_move_logic(fen, time_limit=0.1)
        
        # May succeed or fail depending on Stockfish availability
        if result["success"]:
            assert result["move_uci"] is not None
            assert len(result["move_uci"]) >= 4
        else:
            assert result["error"] is not None
    
    def test_health_check_tool(self):
        """Test health_check logic function."""
        result = health_check_logic()
        
        assert "status" in result
        assert "chess_engine" in result
        assert "stockfish_path" in result
        assert "timestamp" in result
        assert result["status"] in ["healthy", "unhealthy"]


class TestMCPToolChaining:
    """Test chaining MCP tools together."""
    
    def test_validate_then_make_move(self):
        """Test validating then making a move."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        move = "e2e4"
        
        # First validate the move
        validate_result = validate_move_logic(fen, move)
        assert validate_result["valid"] is True
        
        # Then make the move
        make_result = make_move_logic(fen, move)
        assert make_result["success"] is True
        
        # Verify the new position
        new_fen = make_result["new_fen"]
        status_result = get_game_status_logic(new_fen)
        assert status_result["current_turn"] == "black"
    
    def test_stockfish_move_validation_chain(self):
        """Test getting Stockfish move and validating it."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Get Stockfish move
        stockfish_result = get_stockfish_move_logic(fen, time_limit=0.1)
        
        if stockfish_result["success"]:
            move = stockfish_result["move_uci"]
            
            # Validate the Stockfish move
            validate_result = validate_move_logic(fen, move)
            # Stockfish should always return legal moves
            assert validate_result["valid"] is True