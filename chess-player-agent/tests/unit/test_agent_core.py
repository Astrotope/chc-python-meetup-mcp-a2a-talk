"""
Unit tests for chess player agent core functionality.

Tests the stateless agent design and core functions.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from chess_player_agent import (
    create_chess_agent,
    generate_move,
    create_app,
    MoveResponse
)


class TestMoveResponse:
    """Test the MoveResponse pydantic model."""
    
    def test_valid_uci_move(self):
        """Test creating MoveResponse with valid UCI move."""
        response = MoveResponse(move_uci="e2e4")
        assert response.move_uci == "e2e4"
    
    def test_uci_move_with_promotion(self):
        """Test creating MoveResponse with promotion."""
        response = MoveResponse(move_uci="e7e8q")
        assert response.move_uci == "e7e8q"
    
    def test_knight_move(self):
        """Test creating MoveResponse with knight move."""
        response = MoveResponse(move_uci="g1f3")
        assert response.move_uci == "g1f3"


class TestCreateChessAgent:
    """Test chess agent creation."""
    
    @patch('chess_player_agent.MCPServerStreamableHTTP')
    @patch('chess_player_agent.Agent')
    def test_create_agent_configuration(self, mock_agent, mock_mcp_server):
        """Test that agent is created with correct configuration."""
        mock_mcp_instance = Mock()
        mock_mcp_server.return_value = mock_mcp_instance
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        result = create_chess_agent()
        
        # Verify MCP server connection
        mock_mcp_server.assert_called_once()
        
        # Verify agent creation with correct parameters
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args
        
        assert 'model' in call_args.kwargs
        assert 'instructions' in call_args.kwargs
        assert 'toolsets' in call_args.kwargs
        assert 'output_type' in call_args.kwargs
        
        # Verify toolsets includes MCP server
        assert call_args.kwargs['toolsets'] == [mock_mcp_instance]
        
        # Verify output type is MoveResponse
        assert call_args.kwargs['output_type'] == MoveResponse
        
        assert result == mock_agent_instance
    
    def test_agent_instructions_content(self):
        """Test that agent instructions contain required elements."""
        with patch('chess_player_agent.MCPServerStreamableHTTP'), \
             patch('chess_player_agent.Agent') as mock_agent:
            
            create_chess_agent()
            
            call_args = mock_agent.call_args
            instructions = call_args.kwargs['instructions']
            
            # Check for key instruction elements
            assert 'stateless' in instructions.lower()
            assert 'validate_fen' in instructions
            assert 'get_stockfish_move' in instructions
            assert 'validate_move' in instructions
            assert 'uci' in instructions.lower()


class TestGenerateMove:
    """Test the generate_move function."""
    
    @pytest.mark.asyncio
    async def test_generate_move_success(self):
        """Test successful move generation."""
        # Mock the agent and its response
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_result.output = MoveResponse(move_uci="e2e4")
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.return_value = mock_result
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            result = await generate_move(fen)
            
            assert result == "e2e4"
            mock_agent.run.assert_called_once_with(f"Generate the best move for FEN: {fen}")
    
    @pytest.mark.asyncio
    async def test_generate_move_with_promotion(self):
        """Test move generation with pawn promotion."""
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_result.output = MoveResponse(move_uci="e7e8q")
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.return_value = mock_result
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            fen = "rnbqkb1r/ppppPppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
            result = await generate_move(fen)
            
            assert result == "e7e8q"
    
    @pytest.mark.asyncio
    async def test_generate_move_agent_error(self):
        """Test move generation when agent raises error."""
        mock_agent = AsyncMock()
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.side_effect = Exception("MCP server unavailable")
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            with pytest.raises(Exception) as exc_info:
                await generate_move(fen)
            
            assert "MCP server unavailable" in str(exc_info.value)
    
    @pytest.mark.asyncio 
    async def test_generate_move_stateless_behavior(self):
        """Test that generate_move is stateless (no shared state)."""
        mock_agent = AsyncMock()
        mock_result1 = Mock()
        mock_result1.output = MoveResponse(move_uci="e2e4")
        mock_result2 = Mock()
        mock_result2.output = MoveResponse(move_uci="d2d4")
        
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.side_effect = [mock_result1, mock_result2]
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            fen1 = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            fen2 = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            result1 = await generate_move(fen1)
            result2 = await generate_move(fen2)
            
            # Each call should create a new agent (stateless)
            assert result1 == "e2e4"
            assert result2 == "d2d4"
            assert mock_agent.run.call_count == 2


class TestApplicationCreation:
    """Test Starlette application creation."""
    
    @patch('chess_player_agent.create_chess_agent')
    @patch('chess_player_agent.Starlette')
    def test_create_app_structure(self, mock_starlette, mock_create_agent):
        """Test that app is created with correct mount structure."""
        mock_agent = Mock()
        mock_a2a_app = Mock()
        mock_agent.to_a2a.return_value = mock_a2a_app
        mock_create_agent.return_value = mock_agent
        
        mock_health_app = Mock()
        mock_main_app = Mock()
        mock_starlette.side_effect = [mock_health_app, mock_main_app]
        
        result = create_app()
        
        # Verify agent creation and A2A conversion
        mock_create_agent.assert_called_once()
        mock_agent.to_a2a.assert_called_once()
        
        # Verify Starlette app creation calls
        assert mock_starlette.call_count == 2
        
        # Verify the main app is returned
        assert result == mock_main_app
    
    @patch('chess_player_agent.create_chess_agent')
    def test_create_app_mount_paths(self, mock_create_agent):
        """Test that apps are mounted on correct paths."""
        mock_agent = Mock()
        mock_agent.to_a2a.return_value = Mock()
        mock_create_agent.return_value = mock_agent
        
        with patch('chess_player_agent.Starlette') as mock_starlette:
            mock_starlette.return_value = Mock()
            
            create_app()
            
            # Check the main app creation call (second call)
            main_app_call = mock_starlette.call_args_list[1]
            routes = main_app_call.kwargs['routes']
            
            # Should have two mounts
            assert len(routes) == 2
            
            # Check mount paths (this is a simplified check)
            # In reality, we'd need to inspect Mount objects more carefully


class TestStatelessBehavior:
    """Test that the agent maintains stateless behavior."""
    
    @pytest.mark.asyncio
    async def test_no_shared_state_between_calls(self):
        """Test that multiple calls don't share state."""
        # Mock agent that tracks call count
        call_count = 0
        
        def mock_create_agent():
            nonlocal call_count
            call_count += 1
            mock_agent = AsyncMock()
            mock_result = Mock()
            mock_result.output = MoveResponse(move_uci=f"move_{call_count}")
            mock_agent.__aenter__.return_value = mock_agent
            mock_agent.run.return_value = mock_result
            return mock_agent
        
        with patch('chess_player_agent.create_chess_agent', side_effect=mock_create_agent):
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            # Make multiple calls
            result1 = await generate_move(fen)
            result2 = await generate_move(fen)
            result3 = await generate_move(fen)
            
            # Each call should create a new agent instance
            assert call_count == 3
            assert result1 == "move_1"
            assert result2 == "move_2" 
            assert result3 == "move_3"
    
    @pytest.mark.asyncio
    async def test_pure_function_behavior(self):
        """Test that same input produces same output (when mocked consistently)."""
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_result.output = MoveResponse(move_uci="e2e4")
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.return_value = mock_result
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            # Same input should produce same output
            result1 = await generate_move(fen)
            result2 = await generate_move(fen)
            
            assert result1 == result2 == "e2e4"