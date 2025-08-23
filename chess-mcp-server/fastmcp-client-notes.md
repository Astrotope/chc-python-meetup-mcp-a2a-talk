# FastMCP Client Notes

## Key Findings

### Transport Compatibility Issue
- **python-a2a MCPClient**: Only supports SSE (Server-Sent Events) and STDIO transports
- **FastMCP Server**: Provides "streamable HTTP" transport, which is different from SSE
- **Solution**: Use FastMCP's own client which supports streamable HTTP transport

### FastMCP Client Capabilities

#### Supported Transports
1. **STDIO Transport**: Launches server as subprocess with stdin/stdout communication
2. **Streamable HTTP Transport**: Recommended for production, connects to web services
3. **Server-Sent Events (SSE) Transport**: Legacy support for SSE-based servers
4. **In-Memory Transport**: Direct connection within same Python process (testing/dev)
5. **MCP JSON Configuration**: Multi-server configuration file support

#### Basic Usage Pattern
```python
from fastmcp import Client

async def main():
    # Connect to HTTP MCP server
    async with Client("http://localhost:5000/mcp") as client:
        # Ping server
        await client.ping()
        
        # List available tools
        tools = await client.list_tools()
        
        # Call a tool
        result = await client.call_tool("tool_name", {"param": "value"})
        print(result.data)
```

#### Tool Operations
- `list_tools()`: Get available tools
- `call_tool(name, args)`: Execute tool with arguments
- Automatic result deserialization
- Support for complex return types
- Optional timeout and progress tracking

#### Resource Operations
- `list_resources()`: Get static resources
- `list_resource_templates()`: Get resource templates
- `read_resource(uri)`: Read resource content
- Support for text and binary content

#### Prompt Operations
- `list_prompts()`: Get available prompts
- `get_prompt(name, args)`: Retrieve prompt with arguments
- Support for templating with dynamic arguments
- Multi-turn conversation support

#### Authentication
- Bearer token support: `Client(url, auth="token")`
- BearerAuth class: `auth=BearerAuth(token="token")`
- Custom headers: `headers={"X-API-Key": "token"}`
- Only relevant for HTTP transports

## Implementation Strategy

For our chess MCP server testing:
1. Use FastMCP Client instead of python-a2a MCPClient
2. Connect via streamable HTTP transport to `http://localhost:5000/mcp`
3. Test all chess tools: validate_move, make_move, get_stockfish_move, get_game_status, health_check
4. Verify compatibility with our FastMCP server implementation

This approach resolves the transport compatibility issue while maintaining full MCP protocol support.