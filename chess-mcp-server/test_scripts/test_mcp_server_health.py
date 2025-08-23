#!/usr/bin/env python3
"""
Test script for MCP server health and startup.

Tests that the MCP server starts correctly and responds to health checks.
"""
import asyncio
import sys
import os
import time
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_server_startup():
    """Test MCP server startup or check if already running."""
    print("🚀 Testing MCP server startup...")
    
    # First check if server is already running
    try:
        import aiohttp
        test_url = "http://localhost:5000/health"
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                if response.status in [200, 503]:
                    print("  ✅ MCP server already running")
                    return True
    except:
        pass  # Server not running, proceed with startup test
    
    try:
        # Start server in background using the correct command
        server_process = subprocess.Popen(
            [sys.executable, "chess_mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent.parent)
        )
        
        # Wait for server to start
        print("  ⏳ Waiting for server to start...")
        time.sleep(5)  # Give more time for startup
        
        # Check if process is still running
        if server_process.poll() is None:
            print("  ✅ MCP server started successfully")
            
            # Terminate the server
            server_process.terminate()
            server_process.wait(timeout=5)
            return True
        else:
            stdout, stderr = server_process.communicate()
            stderr_text = stderr.decode()
            
            # Check if failure was due to port already in use
            if "address already in use" in stderr_text:
                print("  ⚠️ Port already in use - checking if server is responding...")
                try:
                    import aiohttp
                    test_url = "http://localhost:5000/health"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                            if response.status in [200, 503]:
                                print("  ✅ Server is running on port 5000")
                                return True
                except:
                    pass
            
            print(f"  ❌ Server failed to start")
            print(f"  📝 stderr: {stderr_text}")
            return False
            
    except Exception as e:
        print(f"  ❌ Server startup test failed: {e}")
        if 'server_process' in locals():
            try:
                server_process.terminate()
            except:
                pass
        return False


async def test_health_endpoint():
    """Test health endpoint over HTTP."""
    print("\n💚 Testing health endpoint...")
    
    try:
        import aiohttp
        
        base_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000")
        health_url = f"{base_url}/health"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(health_url) as response:
                if response.status in [200, 503]:  # 503 is OK if some components down
                    data = await response.json()
                    print(f"  ✅ Health endpoint responding")
                    print(f"  📊 Status: {data.get('status', 'unknown')}")
                    print(f"  🔧 Chess engine: {data.get('chess_engine', 'unknown')}")
                    print(f"  🏷️ Service: {data.get('service', 'unknown')}")
                    return True
                else:
                    print(f"  ❌ Unexpected status: {response.status}")
                    return False
                    
    except ImportError:
        print("  ⚠️ aiohttp not installed, skipping HTTP health test")
        return True
    except Exception as e:
        print(f"  ❌ Health endpoint test failed: {e}")
        return False


async def test_mcp_endpoint():
    """Test MCP endpoint availability."""
    print("\n🔗 Testing MCP endpoint...")
    
    try:
        import aiohttp
        
        base_url = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000")
        mcp_url = f"{base_url}/mcp"
        
        # Test with a simple MCP initialize request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                mcp_url, 
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                if response.status == 200:
                    # FastMCP streamable HTTP returns server-sent events
                    response_text = await response.text()
                    if "event: message" in response_text and '"result"' in response_text:
                        print("  ✅ MCP endpoint responding to initialize")
                        print("  📡 Streamable HTTP transport working")
                        return True
                    else:
                        print(f"  ❌ Unexpected MCP response: {response_text}")
                        return False
                else:
                    print(f"  ❌ MCP endpoint status: {response.status}")
                    return False
                    
    except ImportError:
        print("  ⚠️ aiohttp not installed, skipping MCP endpoint test")
        return True
    except Exception as e:
        print(f"  ❌ MCP endpoint test failed: {e}")
        return False


async def test_environment_config():
    """Test environment configuration loading."""
    print("\n⚙️ Testing environment configuration...")
    
    try:
        from chess_mcp_server import health_check_logic
        
        # Call health check to see environment status
        health_data = health_check_logic()
        
        print(f"  📊 Chess engine status: {health_data.get('chess_engine', 'unknown')}")
        print(f"  🔧 Stockfish path: {health_data.get('stockfish_path', 'unknown')}")
        print(f"  ⏰ Health check timestamp: {health_data.get('timestamp', 'unknown')}")
        
        if health_data.get("status") in ["healthy", "unhealthy"]:
            print("  ✅ Environment configuration loaded")
            return True
        else:
            print("  ❌ Environment configuration failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Environment config test failed: {e}")
        return False


def print_config():
    """Print current configuration."""
    print("MCP Server Configuration:")
    print(f"  Server URL: {os.getenv('CHESS_MCP_SERVER_URL', 'http://localhost:5000')}")
    print(f"  Stockfish Path: {os.getenv('STOCKFISH_PATH', 'Default/auto-detect')}")
    print(f"  Python Path: {sys.executable}")
    print(f"  Working Dir: {os.getcwd()}")
    print()


async def main():
    """Run all MCP server health tests."""
    print("Chess MCP Server - Health Test")
    print("=" * 35)
    
    print_config()
    
    # Run tests
    tests = [
        ("Environment Config", test_environment_config),
        ("Server Startup", test_server_startup),
        ("Health Endpoint", test_health_endpoint),
        ("MCP Endpoint", test_mcp_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = await test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 35)
    print("📊 MCP Server Health Test Results")
    print("=" * 35)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🏆 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All MCP server health tests passed!")
    else:
        print("⚠️ Some tests failed - check server configuration")


if __name__ == "__main__":
    asyncio.run(main())