#!/usr/bin/env python3
"""
Test script for FastMCP client connectivity to chess MCP server.

Tests the MCP server using FastMCP client over HTTP transport.
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import Client


async def test_fastmcp_connection():
    """Test basic FastMCP client connection."""
    print("🔗 Testing FastMCP client connection...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            print("  ✅ FastMCP client connected successfully")
            
            # List available tools
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            print(f"  📋 Available tools: {tool_names}")
            
            expected_tools = [
                "validate_fen", "validate_move", "make_move", 
                "get_legal_moves", "get_game_status", "get_stockfish_move", "health_check"
            ]
            
            if all(tool in tool_names for tool in expected_tools):
                print("  ✅ All expected tools available")
                return True
            else:
                missing = [tool for tool in expected_tools if tool not in tool_names]
                print(f"  ❌ Missing tools: {missing}")
                return False
                
    except Exception as e:
        print(f"  ❌ FastMCP connection failed: {e}")
        return False


async def test_validate_fen_tool():
    """Test validate_fen tool via FastMCP."""
    print("\n🔍 Testing validate_fen tool via FastMCP...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            # Test valid FEN
            result = await client.call_tool("validate_fen", {
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            })
            
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if data.get("valid") is True:
                print("  ✅ Valid FEN correctly validated")
            else:
                print("  ❌ Valid FEN rejected")
                return False
            
            # Test invalid FEN
            result = await client.call_tool("validate_fen", {"fen": "invalid_fen"})
            
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if data.get("valid") is False:
                print("  ✅ Invalid FEN correctly rejected")
                return True
            else:
                print("  ❌ Invalid FEN accepted")
                return False
                    
    except Exception as e:
        print(f"  ❌ validate_fen test failed: {e}")
        return False


async def test_get_legal_moves_tool():
    """Test get_legal_moves tool via FastMCP."""
    print("\n♟️ Testing get_legal_moves tool via FastMCP...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            result = await client.call_tool("get_legal_moves", {
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            })
            
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            
            if (data.get("success") is True and 
                data.get("count") == 20 and
                "e2e4" in data.get("legal_moves", [])):
                print(f"  ✅ Legal moves retrieved: {data['count']} moves")
                print(f"  📝 Sample moves: {data['legal_moves'][:5]}...")
                return True
            else:
                print(f"  ❌ Unexpected legal moves result: {data}")
                return False
                    
    except Exception as e:
        print(f"  ❌ get_legal_moves test failed: {e}")
        return False


async def test_make_move_tool():
    """Test make_move tool via FastMCP."""
    print("\n♠️ Testing make_move tool via FastMCP...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            result = await client.call_tool("make_move", {
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "move_uci": "e2e4"
            })
            
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            
            if (data.get("success") is True and 
                " b " in data.get("new_fen", "")):  # Should be black's turn
                print(f"  ✅ Move executed successfully")
                print(f"  📋 New FEN: {data['new_fen']}")
                return True
            else:
                print(f"  ❌ Move execution failed: {data}")
                return False
                    
    except Exception as e:
        print(f"  ❌ make_move test failed: {e}")
        return False


async def test_stockfish_integration():
    """Test Stockfish integration via FastMCP."""
    print("\n🤖 Testing Stockfish integration via FastMCP...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            result = await client.call_tool("get_stockfish_move", {
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "time_limit": 0.1
            })
            
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            
            if data.get("success") is True:
                move = data.get("move_uci")
                if move and len(move) >= 4:
                    print(f"  ✅ Stockfish move received: {move}")
                    return True
                else:
                    print(f"  ❌ Invalid Stockfish move: {move}")
                    return False
            else:
                print(f"  ⚠️ Stockfish not available: {data.get('error')}")
                return True  # Not an error if Stockfish isn't installed
                    
    except Exception as e:
        print(f"  ❌ Stockfish test failed: {e}")
        return False


async def test_health_check():
    """Test health check via FastMCP."""
    print("\n💚 Testing health check via FastMCP...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            result = await client.call_tool("health_check", {})
            
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            
            required_keys = ["status", "chess_engine", "stockfish_path", "timestamp"]
            if all(key in data for key in required_keys):
                print(f"  ✅ Health check passed")
                print(f"  📊 Status: {data['status']}")
                print(f"  🔧 Chess engine: {data['chess_engine']}")
                return True
            else:
                missing = [key for key in required_keys if key not in data]
                print(f"  ❌ Health check missing keys: {missing}")
                return False
                    
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        return False


async def test_complete_workflow():
    """Test complete chess workflow via FastMCP."""
    print("\n🔄 Testing complete chess workflow via FastMCP...")
    
    try:
        server_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
        
        async with Client(server_url) as client:
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            # 1. Validate starting position
            result = await client.call_tool("validate_fen", {"fen": fen})
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if not data.get("valid"):
                print("  ❌ Starting position validation failed")
                return False
            
            # 2. Get legal moves
            result = await client.call_tool("get_legal_moves", {"fen": fen})
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if not data.get("success") or "e2e4" not in data.get("legal_moves", []):
                print("  ❌ Legal moves retrieval failed")
                return False
            
            # 3. Validate specific move
            result = await client.call_tool("validate_move", {
                "fen": fen, 
                "move_uci": "e2e4"
            })
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if not data.get("valid"):
                print("  ❌ Move validation failed")
                return False
            
            # 4. Make the move
            result = await client.call_tool("make_move", {
                "fen": fen,
                "move_uci": "e2e4"
            })
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if not data.get("success"):
                print("  ❌ Move execution failed")
                return False
            
            # 5. Check new game status
            new_fen = data["new_fen"]
            result = await client.call_tool("get_game_status", {"fen": new_fen})
            data = json.loads(result.data) if isinstance(result.data, str) else result.data
            if data.get("current_turn") != "black":
                print("  ❌ Game status check failed")
                return False
            
            print("  ✅ Complete workflow successful")
            return True
            
    except Exception as e:
        print(f"  ❌ Complete workflow failed: {e}")
        return False


def print_config():
    """Print MCP server configuration."""
    print("MCP Server Configuration:")
    print(f"  Server URL: {os.getenv('CHESS_MCP_SERVER_URL', 'http://localhost:5000/mcp')}")
    print(f"  Stockfish Path: {os.getenv('STOCKFISH_PATH', 'Default')}")
    print()


async def main():
    """Run all FastMCP client tests."""
    print("Chess MCP Server - FastMCP Client Test")
    print("=" * 45)
    
    print_config()
    
    # Run tests
    tests = [
        ("FastMCP Connection", test_fastmcp_connection),
        ("Validate FEN Tool", test_validate_fen_tool),
        ("Get Legal Moves Tool", test_get_legal_moves_tool),
        ("Make Move Tool", test_make_move_tool),
        ("Stockfish Integration", test_stockfish_integration),
        ("Health Check", test_health_check),
        ("Complete Workflow", test_complete_workflow),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = await test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 45)
    print("📊 FastMCP Client Test Results")
    print("=" * 45)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🏆 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All FastMCP client tests passed!")
    else:
        print("⚠️ Some tests failed - check MCP server status")


if __name__ == "__main__":
    asyncio.run(main())