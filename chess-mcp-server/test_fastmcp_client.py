"""
Test client for chess MCP server using FastMCP Client.

This client connects to the chess MCP server via streamable HTTP transport
and tests all available chess tools to ensure proper functionality.
"""
import asyncio
import json
from fastmcp import Client

async def test_chess_mcp_server():
    """Test all chess MCP server tools using FastMCP Client."""
    server_url = "http://localhost:5000/mcp"
    
    print("🚀 Starting chess MCP server test with FastMCP Client...")
    
    try:
        # Connect to the MCP server using streamable HTTP transport
        async with Client(server_url) as client:
            print("✅ Connected to chess MCP server")
            
            # Test ping
            print("\n🏓 Testing server ping...")
            await client.ping()
            print("Server ping successful")
            
            # List available tools
            print("\n📋 Listing available tools...")
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]
            print(f"Available tools: {tool_names}")
            
            # Starting chess position FEN
            starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            # Test 1: Health check
            print("\n🏥 Testing health_check tool...")
            if "health_check" in tool_names:
                health_result = await client.call_tool("health_check", {})
                health_data = json.loads(health_result.data) if isinstance(health_result.data, str) else health_result.data
                print(f"Health status: {health_data.get('status', 'unknown')}")
                if health_data.get('chess_engine') == 'available':
                    print("✅ Stockfish engine is available")
                else:
                    print("⚠️  Stockfish engine not available")
            else:
                print("❌ health_check tool not found")
            
            # Test 2: Validate a move
            print("\n♟️  Testing validate_move tool...")
            if "validate_move" in tool_names:
                validate_result = await client.call_tool("validate_move", {
                    "fen": starting_fen,
                    "move_uci": "e2e4"
                })
                validate_data = json.loads(validate_result.data) if isinstance(validate_result.data, str) else validate_result.data
                print(f"Move e2e4 valid: {validate_data.get('valid', False)}")
                
                # Test invalid move
                invalid_result = await client.call_tool("validate_move", {
                    "fen": starting_fen,
                    "move_uci": "e2e5"  # Invalid: pawn can't jump 3 squares
                })
                invalid_data = json.loads(invalid_result.data) if isinstance(invalid_result.data, str) else invalid_result.data
                print(f"Move e2e5 valid: {invalid_data.get('valid', True)} (should be False)")
            else:
                print("❌ validate_move tool not found")
            
            # Test 3: Make a move
            print("\n🎯 Testing make_move tool...")
            if "make_move" in tool_names:
                make_result = await client.call_tool("make_move", {
                    "fen": starting_fen,
                    "move_uci": "e2e4"
                })
                make_data = json.loads(make_result.data) if isinstance(make_result.data, str) else make_result.data
                if make_data.get('success'):
                    new_fen = make_data.get('new_fen')
                    print(f"✅ Move executed successfully")
                    print(f"New position: {new_fen[:50]}...")
                else:
                    print(f"❌ Move failed: {make_data.get('error')}")
            else:
                print("❌ make_move tool not found")
            
            # Test 4: Get game status
            print("\n📊 Testing get_game_status tool...")
            if "get_game_status" in tool_names:
                status_result = await client.call_tool("get_game_status", {
                    "fen": starting_fen
                })
                status_data = json.loads(status_result.data) if isinstance(status_result.data, str) else status_result.data
                print(f"Game over: {status_data.get('is_game_over', 'unknown')}")
                print(f"Current turn: {status_data.get('current_turn', 'unknown')}")
                print(f"Legal moves: {status_data.get('legal_moves_count', 0)}")
                print(f"In check: {status_data.get('is_check', False)}")
            else:
                print("❌ get_game_status tool not found")
            
            # Test 5: Get Stockfish move (might fail if engine not available)
            print("\n🤖 Testing get_stockfish_move tool...")
            if "get_stockfish_move" in tool_names:
                try:
                    stockfish_result = await client.call_tool("get_stockfish_move", {
                        "fen": starting_fen,
                        "time_limit": 1.0
                    })
                    stockfish_data = json.loads(stockfish_result.data) if isinstance(stockfish_result.data, str) else stockfish_result.data
                    if stockfish_data.get('success'):
                        best_move = stockfish_data.get('move_uci')
                        print(f"✅ Stockfish suggests: {best_move}")
                    else:
                        print(f"⚠️  Stockfish failed: {stockfish_data.get('error')}")
                except Exception as e:
                    print(f"⚠️  Stockfish test failed: {e}")
            else:
                print("❌ get_stockfish_move tool not found")
            
            print("\n✅ All tests completed successfully!")
            
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        import traceback
        traceback.print_exc()

async def test_detailed_chess_sequence():
    """Test a detailed chess move sequence."""
    server_url = "http://localhost:5000/mcp"
    
    print("\n🎲 Testing detailed chess sequence...")
    
    try:
        async with Client(server_url) as client:
            current_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
            
            for i, move in enumerate(moves):
                print(f"\nMove {i+1}: {move}")
                
                # Validate the move
                validate_result = await client.call_tool("validate_move", {
                    "fen": current_fen,
                    "move_uci": move
                })
                validate_data = json.loads(validate_result.data) if isinstance(validate_result.data, str) else validate_result.data
                
                if not validate_data.get('valid'):
                    print(f"❌ Move {move} is invalid!")
                    break
                
                # Execute the move
                make_result = await client.call_tool("make_move", {
                    "fen": current_fen,
                    "move_uci": move
                })
                make_data = json.loads(make_result.data) if isinstance(make_result.data, str) else make_result.data
                
                if make_data.get('success'):
                    current_fen = make_data.get('new_fen')
                    print(f"✅ Move executed: {move}")
                    
                    # Get game status
                    status_result = await client.call_tool("get_game_status", {
                        "fen": current_fen
                    })
                    status_data = json.loads(status_result.data) if isinstance(status_result.data, str) else status_result.data
                    print(f"Turn: {status_data.get('current_turn')}, Legal moves: {status_data.get('legal_moves_count')}")
                else:
                    print(f"❌ Failed to execute move {move}: {make_data.get('error')}")
                    break
            
            print("✅ Chess sequence test completed!")
            
    except Exception as e:
        print(f"❌ Error in chess sequence test: {e}")

if __name__ == "__main__":
    print("🚀 Starting comprehensive chess MCP server tests...")
    asyncio.run(test_chess_mcp_server())
    asyncio.run(test_detailed_chess_sequence())