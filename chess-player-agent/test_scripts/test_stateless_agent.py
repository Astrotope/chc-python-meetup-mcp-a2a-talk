#!/usr/bin/env python3
"""
Test script for the stateless chess player agent.

Tests the new stateless architecture with generate_move function.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chess_player_agent import generate_move, create_app
from starlette.testclient import TestClient


async def test_generate_move():
    """Test the core generate_move function."""
    print("🔍 Testing generate_move function...")
    
    test_positions = [
        {
            "name": "Starting position",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        },
        {
            "name": "King's pawn opening",
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        }
    ]
    
    for position in test_positions:
        print(f"  Testing: {position['name']}")
        try:
            move = await generate_move(position['fen'])
            print(f"    Generated move: {move}")
            
            # Validate UCI format
            if len(move) >= 4 and all(c in 'abcdefgh12345678qrbn' for c in move):
                print("    ✅ Valid UCI format")
            else:
                print("    ❌ Invalid UCI format")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")


def test_health_endpoint():
    """Test the health check endpoint."""
    print("\n💚 Testing health endpoint...")
    
    try:
        app = create_app()
        client = TestClient(app)
        
        response = client.get("/health")
        print(f"  Status: {response.status_code}")
        
        if response.status_code in [200, 503]:  # 503 is OK if MCP server down
            data = response.json()
            print(f"  Health status: {data.get('status', 'unknown')}")
            print(f"  MCP server: {data.get('mcp_server', 'unknown')}")
            print("  ✅ Health endpoint responding")
        else:
            print(f"  ❌ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Health endpoint error: {e}")


def test_app_routing():
    """Test application routing structure."""
    print("\n🛤️ Testing app routing...")
    
    try:
        app = create_app()
        client = TestClient(app)
        
        # Test health route
        health_response = client.get("/health")
        print(f"  /health: {health_response.status_code}")
        
        # Test root route (A2A)
        root_response = client.get("/")
        print(f"  /: {root_response.status_code}")
        
        if health_response.status_code in [200, 503] and root_response.status_code != 404:
            print("  ✅ Routing structure correct")
        else:
            print("  ❌ Routing issues detected")
            
    except Exception as e:
        print(f"  ❌ Routing test error: {e}")


async def test_stateless_property():
    """Test that the agent is truly stateless."""
    print("\n🔄 Testing stateless property...")
    
    try:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Multiple calls should work independently
        move1 = await generate_move(fen)
        move2 = await generate_move(fen)
        
        print(f"  Call 1: {move1}")
        print(f"  Call 2: {move2}")
        
        # Check that both calls succeeded
        if move1 and move2:
            print("  ✅ Multiple calls successful (stateless)")
        else:
            print("  ❌ Calls failed")
            
    except Exception as e:
        print(f"  ❌ Stateless test error: {e}")


async def test_error_handling():
    """Test error handling."""
    print("\n⚠️ Testing error handling...")
    
    # Test invalid FEN
    try:
        await generate_move("invalid_fen")
        print("  ❌ Should have failed with invalid FEN")
    except Exception:
        print("  ✅ Correctly rejected invalid FEN")
    
    # Test empty input
    try:
        await generate_move("")
        print("  ❌ Should have failed with empty FEN")
    except Exception:
        print("  ✅ Correctly rejected empty FEN")


def print_config():
    """Print current configuration."""
    print("Configuration:")
    print(f"  OpenAI API Key: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    print(f"  MCP Server URL: {os.getenv('CHESS_MCP_SERVER_URL', 'Default')}")
    print(f"  Agent Model: {os.getenv('AGENT_MODEL', 'Default')}")
    print(f"  Agent Name: {os.getenv('AGENT_NAME', 'Default')}")


async def main():
    """Run all tests."""
    print("Chess Player Agent - Stateless Architecture Test")
    print("=" * 50)
    
    print_config()
    print()
    
    # Run tests
    await test_generate_move()
    test_health_endpoint()
    test_app_routing()
    await test_stateless_property()
    await test_error_handling()
    
    print("\n" + "=" * 50)
    print("✅ Test script completed!")


if __name__ == "__main__":
    asyncio.run(main())