"""
Unit tests for health check endpoint functionality.

Tests the health check logic and HTTP endpoint behavior.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from starlette.testclient import TestClient
from starlette.responses import JSONResponse
from chess_player_agent import health_check, create_app


class TestHealthCheckFunction:
    """Test the health_check function."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        # Mock the agent and successful MCP interaction
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.return_value = mock_result
        
        mock_request = Mock()
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            response = await health_check(mock_request)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 200
            
            # Parse response content
            content = response.body.decode()
            assert '"status":"healthy"' in content
            assert '"mcp_server":"available"' in content
    
    @pytest.mark.asyncio
    async def test_health_check_mcp_failure(self):
        """Test health check when MCP server is unavailable."""
        mock_agent = AsyncMock()
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.side_effect = Exception("Connection refused")
        
        mock_request = Mock()
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            response = await health_check(mock_request)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 503
            
            content = response.body.decode()
            assert '"status":"unhealthy"' in content
            assert '"mcp_server":"unavailable"' in content
            assert '"error":"Connection refused"' in content
    
    @pytest.mark.asyncio
    async def test_health_check_agent_creation_failure(self):
        """Test health check when agent creation fails."""
        mock_request = Mock()
        
        with patch('chess_player_agent.create_chess_agent', side_effect=Exception("No API key")):
            response = await health_check(mock_request)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 503
            
            content = response.body.decode()
            assert '"status":"unhealthy"' in content
            assert '"error":"No API key"' in content
    
    @pytest.mark.asyncio
    async def test_health_check_response_structure(self):
        """Test that health check response has required structure."""
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.return_value = mock_result
        
        mock_request = Mock()
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent), \
             patch('chess_player_agent.CHESS_MCP_SERVER_URL', 'http://test:5000/mcp'), \
             patch('chess_player_agent.AGENT_NAME', 'test-agent'), \
             patch('chess_player_agent.AGENT_MODEL', 'test-model'):
            
            response = await health_check(mock_request)
            
            content = response.body.decode()
            
            # Check required fields are present
            assert '"mcp_server_url":"http://test:5000/mcp"' in content
            assert '"agent_name":"test-agent"' in content
            assert '"model":"test-model"' in content
    
    @pytest.mark.asyncio
    async def test_health_check_uses_test_fen(self):
        """Test that health check uses standard starting position for testing."""
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_agent.__aenter__.return_value = mock_agent
        mock_agent.run.return_value = mock_result
        
        mock_request = Mock()
        
        with patch('chess_player_agent.create_chess_agent', return_value=mock_agent):
            await health_check(mock_request)
            
            # Verify the FEN validation call
            mock_agent.run.assert_called_once()
            call_args = mock_agent.run.call_args[0][0]
            
            assert "validate_fen" in call_args
            assert "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" in call_args


class TestHealthEndpointIntegration:
    """Test health endpoint integration with Starlette app."""
    
    def test_health_endpoint_exists(self):
        """Test that health endpoint is accessible."""
        # Mock the create_chess_agent function to avoid actual MCP calls
        with patch('chess_player_agent.create_chess_agent') as mock_create:
            # Create a proper async mock agent
            mock_agent = AsyncMock()
            mock_agent.__aenter__.return_value = mock_agent
            mock_agent.run.return_value = Mock(output=Mock(move_uci="e2e4"))
            mock_create.return_value = mock_agent
            
            app = create_app()
            client = TestClient(app)
            
            response = client.get("/health")
            
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    def test_health_endpoint_path(self):
        """Test that health endpoint is accessible at correct path."""
        with patch('chess_player_agent.create_chess_agent') as mock_create:
            # Create a proper async mock agent
            mock_agent = AsyncMock()
            mock_agent.__aenter__.return_value = mock_agent
            mock_agent.run.return_value = Mock(output=Mock(move_uci="e2e4"))
            mock_create.return_value = mock_agent
            
            app = create_app()
            client = TestClient(app)
            
            # Should be accessible at /health
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    def test_health_endpoint_method(self):
        """Test that health endpoint only accepts GET requests."""
        with patch('chess_player_agent.create_chess_agent') as mock_create:
            # Create a proper async mock agent
            mock_agent = AsyncMock()
            mock_agent.__aenter__.return_value = mock_agent
            mock_agent.run.return_value = Mock(output=Mock(move_uci="e2e4"))
            mock_create.return_value = mock_agent
            
            app = create_app()
            client = TestClient(app)
            
            # GET should work
            response = client.get("/health")
            assert response.status_code == 200
            
            # POST should not be allowed
            response = client.post("/health")
            assert response.status_code == 405  # Method Not Allowed
    
    def test_health_endpoint_content_type(self):
        """Test that health endpoint returns JSON."""
        with patch('chess_player_agent.create_chess_agent') as mock_create:
            # Create a proper async mock agent
            mock_agent = AsyncMock()
            mock_agent.__aenter__.return_value = mock_agent
            mock_agent.run.return_value = Mock(output=Mock(move_uci="e2e4"))
            mock_create.return_value = mock_agent
            
            app = create_app()
            client = TestClient(app)
            
            response = client.get("/health")
            
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]
            assert response.json()["status"] == "healthy"


class TestAppMountStructure:
    """Test that the application mount structure is correct."""
    
    def test_both_endpoints_exist(self):
        """Test that both health and A2A endpoints exist."""
        with patch('chess_player_agent.create_chess_agent') as mock_create:
            mock_agent = Mock()
            mock_a2a_app = Mock()
            mock_agent.to_a2a.return_value = mock_a2a_app
            mock_create.return_value = mock_agent
            
            app = create_app()
            client = TestClient(app)
            
            with patch('chess_player_agent.health_check') as mock_health:
                mock_response = JSONResponse({"status": "healthy"})
                mock_health.return_value = mock_response
                
                # Health endpoint should be accessible
                response = client.get("/health")
                assert response.status_code == 200
                
                # Root should be accessible (A2A endpoint)
                # Note: This might return different status depending on A2A implementation
                response = client.get("/")
                # Just check that it doesn't return 404 (endpoint exists)
                assert response.status_code != 404
    
    def test_mount_isolation(self):
        """Test that mounted apps are isolated."""
        with patch('chess_player_agent.create_chess_agent'):
            app = create_app()
            client = TestClient(app)
            
            with patch('chess_player_agent.health_check') as mock_health:
                mock_response = JSONResponse({"status": "healthy"})
                mock_health.return_value = mock_response
                
                # Health endpoint should not be accessible at root
                response = client.get("/health")
                assert response.status_code == 200
                
                # Health function should only be called for /health, not /
                mock_health.reset_mock()
                client.get("/")
                mock_health.assert_not_called()