"""
Simple HTTP test client for chess MCP server.

This client makes direct HTTP requests to test the MCP protocol endpoints.
"""
import json
import requests

def test_mcp_http_endpoint():
    """Test the MCP server with direct HTTP requests."""
    base_url = "http://localhost:5000/mcp"
    
    print("🚀 Testing chess MCP server with HTTP requests...")
    
    # Test 1: Initialize connection
    print("\n🔌 Testing MCP initialization...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    session_id = None
    
    try:
        response = requests.post(base_url, 
                               json=init_request, 
                               headers=headers,
                               timeout=10)
        print(f"Initialize response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Raw response: {response.text[:500]}...")  # Show first 500 chars
        
        if response.status_code == 200:
            try:
                # Try to parse as JSON first
                init_result = response.json()
                print(f"Initialize result: {json.dumps(init_result, indent=2)}")
            except json.JSONDecodeError:
                # If not JSON, it might be SSE format
                print("Response is not JSON, likely SSE format. Parsing SSE...")
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            print(f"SSE data: {json.dumps(data, indent=2)}")
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse SSE data: {line}, error: {e}")
        else:
            print(f"Initialize failed: {response.text}")
            return
        
        # Test 2: List tools
        print("\n📋 Testing tools listing...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = requests.post(base_url, 
                               json=list_tools_request, 
                               headers=headers,
                               timeout=10)
        print(f"List tools response status: {response.status_code}")
        if response.status_code == 200:
            tools_result = response.json()
            print(f"Available tools: {json.dumps(tools_result, indent=2)}")
            
            # Extract tool names for further testing
            if 'result' in tools_result and 'tools' in tools_result['result']:
                tool_names = [tool['name'] for tool in tools_result['result']['tools']]
                print(f"Tool names: {tool_names}")
                
                # Test 3: Call a tool (health_check)
                if 'health_check' in tool_names:
                    print("\n🏥 Testing health_check tool...")
                    tool_call_request = {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "health_check",
                            "arguments": {}
                        }
                    }
                    
                    response = requests.post(base_url, 
                                           json=tool_call_request, 
                                           headers=headers,
                                           timeout=10)
                    print(f"Health check response status: {response.status_code}")
                    if response.status_code == 200:
                        health_result = response.json()
                        print(f"Health check result: {json.dumps(health_result, indent=2)}")
                    else:
                        print(f"Health check failed: {response.text}")
        else:
            print(f"List tools failed: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP request error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_mcp_http_endpoint()