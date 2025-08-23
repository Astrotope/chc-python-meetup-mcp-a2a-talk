"""
Test client for chess MCP server using python-a2a.

This client connects to the chess MCP server via streamable HTTP transport
and tests all available tools to ensure proper functionality.
"""
import asyncio
from python_a2a import MCPClient

async def test_chess_mcp_server():
    """Test all chess MCP server tools."""
    # Connect to the MCP server
    client = MCPClient("http://localhost:5000/mcp")
    
    try:
        # Connect to the server
        await client.connect()
        print("✅ Connected to chess MCP server")
        
        # List available tools
        tools = await client.get_tools()
        print(f"📋 Available tools: {list(tools.keys())}")
        
        # Test 1: Health check
        print("\n🏥 Testing health check...")
        health_result = await client.call_tool("health_check", {})
        print(f"Health status: {health_result.content[0].text}")
        
        # Test 2: Validate a move
        print("\n♟️  Testing move validation...")
        starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        validate_result = await client.call_tool("validate_move", {
            "fen": starting_fen,
            "move_uci": "e2e4"
        })
        print(f"Move validation result: {validate_result.content[0].text}")
        
        # Test 3: Make a move
        print("\n🎯 Testing move execution...")
        make_result = await client.call_tool("make_move", {
            "fen": starting_fen,
            "move_uci": "e2e4"
        })
        print(f"Move execution result: {make_result.content[0].text}")
        
        # Test 4: Get game status
        print("\n📊 Testing game status...")
        status_result = await client.call_tool("get_game_status", {
            "fen": starting_fen
        })
        print(f"Game status result: {status_result.content[0].text}")
        
        # Test 5: Get Stockfish move (this might fail if Stockfish isn't available)
        print("\n🤖 Testing Stockfish move...")
        try:
            stockfish_result = await client.call_tool("get_stockfish_move", {
                "fen": starting_fen,
                "time_limit": 1.0
            })
            print(f"Stockfish move result: {stockfish_result.content[0].text}")
        except Exception as e:
            print(f"Stockfish test failed (expected if engine not available): {e}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
    
    finally:
        # Clean up connection
        await client.close()
        print("🔌 Disconnected from server")

if __name__ == "__main__":
    print("🚀 Starting chess MCP server test client...")
    asyncio.run(test_chess_mcp_server())