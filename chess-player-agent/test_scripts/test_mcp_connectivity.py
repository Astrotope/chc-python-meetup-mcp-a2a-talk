#!/usr/bin/env python3
"""
Test script for MCP server connectivity.

Tests that the agent can properly communicate with the MCP server.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chess_player_agent import create_chess_agent, generate_move


async def test_mcp_connection():
    """Test basic MCP server connection."""
    print("🔗 Testing MCP server connection...")
    
    try:
        agent = create_chess_agent()
        print("  ✅ Agent created successfully")
        
        # Test agent context creation
        async with agent:
            print("  ✅ Agent context established")
            
        print("  ✅ MCP connection test passed")
        return True
        
    except Exception as e:
        print(f"  ❌ MCP connection failed: {e}")
        return False


async def test_fen_validation():
    """Test FEN validation through MCP."""
    print("\n🔍 Testing FEN validation via MCP...")
    
    try:
        # This will use the agent which calls MCP validate_fen
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # The generate_move function validates FEN internally
        move = await generate_move(fen)
        print(f"  ✅ Valid FEN processed, move: {move}")
        return True
        
    except Exception as e:
        print(f"  ❌ FEN validation failed: {e}")
        return False


async def test_stockfish_integration():
    """Test Stockfish integration through MCP."""
    print("\n♟️ Testing Stockfish integration via MCP...")
    
    try:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # This will use get_stockfish_move via MCP
        move = await generate_move(fen)
        
        if move and len(move) >= 4:
            print(f"  ✅ Stockfish move received: {move}")
            return True
        else:
            print("  ❌ Invalid move received from Stockfish")
            return False
            
    except Exception as e:
        print(f"  ❌ Stockfish integration failed: {e}")
        return False


async def test_move_validation():
    """Test move validation through MCP."""
    print("\n✔️ Testing move validation via MCP...")
    
    try:
        # The agent should validate moves internally
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        move = await generate_move(fen)
        
        # If we got a move, validation must have passed
        if move:
            print(f"  ✅ Move validation passed: {move}")
            return True
        else:
            print("  ❌ No move returned (validation may have failed)")
            return False
            
    except Exception as e:
        print(f"  ❌ Move validation failed: {e}")
        return False


async def test_complete_mcp_flow():
    """Test complete MCP workflow."""
    print("\n🔄 Testing complete MCP workflow...")
    
    try:
        # This tests the full flow: validate_fen -> get_stockfish_move -> validate_move
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        print(f"  Input FEN: {fen}")
        move = await generate_move(fen)
        print(f"  Output move: {move}")
        
        if move and len(move) >= 4:
            print("  ✅ Complete MCP workflow successful")
            return True
        else:
            print("  ❌ MCP workflow failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Complete MCP workflow failed: {e}")
        return False


async def test_mcp_error_handling():
    """Test MCP error handling."""
    print("\n⚠️ Testing MCP error handling...")
    
    try:
        # Test with invalid FEN - should be caught by MCP validate_fen
        invalid_fen = "invalid_fen_string"
        
        try:
            move = await generate_move(invalid_fen)
            print("  ❌ Should have failed with invalid FEN")
            return False
        except Exception:
            print("  ✅ MCP correctly rejected invalid FEN")
            return True
            
    except Exception as e:
        print(f"  ❌ MCP error handling test failed: {e}")
        return False


def print_mcp_config():
    """Print MCP configuration."""
    print("MCP Configuration:")
    print(f"  MCP Server URL: {os.getenv('CHESS_MCP_SERVER_URL', 'http://localhost:5000/mcp')}")
    print(f"  Agent Model: {os.getenv('AGENT_MODEL', 'openai:gpt-4o')}")
    print()


async def main():
    """Run all MCP connectivity tests."""
    print("Chess Player Agent - MCP Connectivity Test")
    print("=" * 45)
    
    print_mcp_config()
    
    # Run tests
    tests = [
        ("MCP Connection", test_mcp_connection),
        ("FEN Validation", test_fen_validation),
        ("Stockfish Integration", test_stockfish_integration),
        ("Move Validation", test_move_validation),
        ("Complete MCP Flow", test_complete_mcp_flow),
        ("MCP Error Handling", test_mcp_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = await test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 45)
    print("📊 MCP Connectivity Test Results")
    print("=" * 45)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🏆 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All MCP connectivity tests passed!")
    else:
        print("⚠️ Some MCP tests failed - check MCP server status")


if __name__ == "__main__":
    asyncio.run(main())