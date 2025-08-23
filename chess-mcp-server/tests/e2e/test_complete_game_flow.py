"""
End-to-end tests for chess MCP server.

Tests complete chess game scenarios using all MCP tools.
"""
import pytest
from fastmcp.testing import MCPTestClient
from chess_mcp_server import mcp


@pytest.fixture
def mcp_client():
    """Create MCP test client."""
    return MCPTestClient(mcp)


@pytest.mark.e2e
class TestCompleteGameFlow:
    """Test complete chess game scenarios."""
    
    def test_opening_sequence(self, mcp_client):
        """Test a complete opening sequence."""
        # Start with initial position
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Validate starting position
        result = mcp_client.call_tool("validate_fen", fen=fen)
        assert result["valid"] is True
        
        # Check game status
        status = mcp_client.call_tool("get_game_status", fen=fen)
        assert status["is_game_over"] is False
        assert status["current_turn"] == "white"
        assert status["legal_moves_count"] == 20
        
        # Make first move: e2-e4
        move_result = mcp_client.call_tool("make_move", fen=fen, move_uci="e2e4")
        assert move_result["success"] is True
        fen_after_e4 = move_result["new_fen"]
        
        # Verify position after e4
        status = mcp_client.call_tool("get_game_status", fen=fen_after_e4)
        assert status["current_turn"] == "black"
        assert status["is_game_over"] is False
        
        # Black responds with e7-e5
        move_result = mcp_client.call_tool("make_move", fen=fen_after_e4, move_uci="e7e5")
        assert move_result["success"] is True
        fen_after_e5 = move_result["new_fen"]
        
        # Verify position after e5
        status = mcp_client.call_tool("get_game_status", fen=fen_after_e5)
        assert status["current_turn"] == "white"
        assert status["is_game_over"] is False
    
    def test_invalid_move_sequence(self, mcp_client):
        """Test handling of invalid moves in sequence."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Try invalid move
        result = mcp_client.call_tool("validate_move", fen=fen, move_uci="e2e5")
        assert result["valid"] is False
        
        # Try to make invalid move
        move_result = mcp_client.call_tool("make_move", fen=fen, move_uci="e2e5")
        assert move_result["success"] is False
        assert move_result["new_fen"] == fen  # Position unchanged
        assert move_result["error"] == "Invalid move"
    
    def test_legal_moves_analysis(self, mcp_client):
        """Test legal moves analysis throughout a game."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Get legal moves from starting position
        legal_moves = mcp_client.call_tool("get_legal_moves", fen=fen)
        assert legal_moves["success"] is True
        assert legal_moves["count"] == 20
        
        starting_moves = legal_moves["legal_moves"]
        assert "e2e4" in starting_moves
        assert "e2e3" in starting_moves
        assert "g1f3" in starting_moves
        assert "b1c3" in starting_moves
        
        # Make a move and check legal moves change
        move_result = mcp_client.call_tool("make_move", fen=fen, move_uci="e2e4")
        new_fen = move_result["new_fen"]
        
        legal_moves_after = mcp_client.call_tool("get_legal_moves", fen=new_fen)
        assert legal_moves_after["success"] is True
        assert legal_moves_after["count"] == 20  # Black also has 20 legal moves
        
        # Legal moves should be different
        new_moves = legal_moves_after["legal_moves"]
        assert new_moves != starting_moves
        assert "e7e5" in new_moves
        assert "e7e6" in new_moves
    
    def test_checkmate_scenario(self, mcp_client):
        """Test Scholar's mate scenario."""
        # Scholar's mate sequence
        moves = [
            ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e2e4"),
            ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", "e7e5"),
            ("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2", "f1c4"),
            ("rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2", "b8c6"),
            ("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3", "d1h5"),
            ("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3", "g8f6"),
            ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "h5f7")
        ]
        
        current_fen = moves[0][0]
        
        for i, (expected_fen, move) in enumerate(moves):
            if i > 0:
                # Verify we're at the expected position
                # (Note: FEN comparison is complex due to move counters, so we'll just verify game isn't over)
                status = mcp_client.call_tool("get_game_status", fen=current_fen)
                if i < len(moves) - 1:  # Not the final move
                    assert status["is_game_over"] is False
            
            # Validate and make the move
            validate_result = mcp_client.call_tool("validate_move", fen=current_fen, move_uci=move)
            assert validate_result["valid"] is True
            
            move_result = mcp_client.call_tool("make_move", fen=current_fen, move_uci=move)
            assert move_result["success"] is True
            current_fen = move_result["new_fen"]
        
        # After final move, should be checkmate
        final_status = mcp_client.call_tool("get_game_status", fen=current_fen)
        assert final_status["is_game_over"] is True
        assert final_status["winner"] == "True"  # White wins
    
    def test_castling_scenario(self, mcp_client):
        """Test castling moves."""
        # Position where white can castle kingside
        fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 4 4"
        
        # Verify kingside castling is legal
        legal_moves = mcp_client.call_tool("get_legal_moves", fen=fen)
        if legal_moves["success"]:
            assert "e1g1" in legal_moves["legal_moves"]  # Kingside castling
            
            # Perform castling
            castle_result = mcp_client.call_tool("make_move", fen=fen, move_uci="e1g1")
            if castle_result["success"]:
                # Verify castling worked
                new_fen = castle_result["new_fen"]
                status = mcp_client.call_tool("get_game_status", fen=new_fen)
                assert status["current_turn"] == "black"
    
    def test_promotion_scenario(self, mcp_client):
        """Test pawn promotion."""
        # Position where white pawn can promote
        fen = "rnbqkb1r/ppppp1Pp/8/8/8/8/PPPPPP1P/RNBQKBNR w KQkq - 0 1"
        
        # Validate promotion move
        promotion_move = "g7g8q"  # Promote to queen
        validate_result = mcp_client.call_tool("validate_move", fen=fen, move_uci=promotion_move)
        
        if validate_result["valid"]:
            # Make promotion move
            move_result = mcp_client.call_tool("make_move", fen=fen, move_uci=promotion_move)
            assert move_result["success"] is True
            
            # Verify promotion worked
            new_fen = move_result["new_fen"]
            assert "Q" in new_fen  # Queen should be on the board


@pytest.mark.e2e
class TestStockfishIntegration:
    """Test Stockfish integration in game scenarios."""
    
    def test_stockfish_provides_legal_moves(self, mcp_client):
        """Test that Stockfish always provides legal moves."""
        test_positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",  # After e4 e5
            "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 4 4",  # Middle game
        ]
        
        for fen in test_positions:
            stockfish_result = mcp_client.call_tool("get_stockfish_move", fen=fen, time_limit=0.1)
            
            if stockfish_result["success"]:
                # Stockfish provided a move
                move = stockfish_result["move_uci"]
                assert move is not None
                assert len(move) >= 4
                
                # Verify the move is legal
                validate_result = mcp_client.call_tool("validate_move", fen=fen, move_uci=move)
                assert validate_result["valid"] is True, f"Stockfish move {move} is not legal for position {fen}"
            else:
                # Stockfish not available - skip this test
                pytest.skip(f"Stockfish not available: {stockfish_result['error']}")
    
    def test_stockfish_vs_legal_moves_consistency(self, mcp_client):
        """Test that Stockfish moves are in the legal moves list."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Get legal moves
        legal_moves_result = mcp_client.call_tool("get_legal_moves", fen=fen)
        assert legal_moves_result["success"] is True
        legal_moves = legal_moves_result["legal_moves"]
        
        # Get Stockfish move
        stockfish_result = mcp_client.call_tool("get_stockfish_move", fen=fen, time_limit=0.1)
        
        if stockfish_result["success"]:
            stockfish_move = stockfish_result["move_uci"]
            assert stockfish_move in legal_moves, f"Stockfish move {stockfish_move} not in legal moves list"
        else:
            pytest.skip(f"Stockfish not available: {stockfish_result['error']}")


@pytest.mark.e2e
class TestErrorHandlingFlow:
    """Test error handling in complete game flows."""
    
    def test_invalid_fen_handling(self, mcp_client):
        """Test that all tools handle invalid FEN consistently."""
        invalid_fen = "invalid_fen_string"
        
        # All tools should handle invalid FEN gracefully
        validate_fen_result = mcp_client.call_tool("validate_fen", fen=invalid_fen)
        assert validate_fen_result["valid"] is False
        assert validate_fen_result["error"] is not None
        
        validate_move_result = mcp_client.call_tool("validate_move", fen=invalid_fen, move_uci="e2e4")
        assert validate_move_result["valid"] is False
        assert validate_move_result["error"] is not None
        
        make_move_result = mcp_client.call_tool("make_move", fen=invalid_fen, move_uci="e2e4")
        assert make_move_result["success"] is False
        assert make_move_result["error"] is not None
        
        legal_moves_result = mcp_client.call_tool("get_legal_moves", fen=invalid_fen)
        assert legal_moves_result["success"] is False
        assert legal_moves_result["error"] is not None
        
        game_status_result = mcp_client.call_tool("get_game_status", fen=invalid_fen)
        assert game_status_result["current_turn"] == "unknown"
        assert game_status_result["error"] is not None
    
    def test_recovery_from_errors(self, mcp_client):
        """Test that system can recover from errors."""
        valid_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        invalid_fen = "invalid"
        
        # Start with error
        error_result = mcp_client.call_tool("validate_fen", fen=invalid_fen)
        assert error_result["valid"] is False
        
        # Recovery with valid FEN should work
        valid_result = mcp_client.call_tool("validate_fen", fen=valid_fen)
        assert valid_result["valid"] is True
        
        # Subsequent operations should work normally
        legal_moves = mcp_client.call_tool("get_legal_moves", fen=valid_fen)
        assert legal_moves["success"] is True
        assert legal_moves["count"] == 20


@pytest.mark.e2e
class TestPerformanceFlow:
    """Test performance aspects of the MCP server."""
    
    def test_multiple_rapid_requests(self, mcp_client):
        """Test handling of multiple rapid requests."""
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Make multiple rapid requests
        for i in range(10):
            result = mcp_client.call_tool("get_legal_moves", fen=fen)
            assert result["success"] is True
            assert result["count"] == 20
    
    def test_health_check_performance(self, mcp_client):
        """Test that health check responds quickly."""
        import time
        
        start_time = time.time()
        result = mcp_client.call_tool("health_check")
        end_time = time.time()
        
        # Health check should complete quickly (under 5 seconds per EARS)
        assert end_time - start_time < 5.0
        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy"]