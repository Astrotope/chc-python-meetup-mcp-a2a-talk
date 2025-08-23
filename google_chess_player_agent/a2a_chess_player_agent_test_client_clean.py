#!/usr/bin/env python3
"""
A2A Chess Player Agent Test Client - Clean DRY Version

Test client for the Google A2A chess player agent.
Based on currency-agent test_client.py pattern from Google ADK examples.
"""
import asyncio
import os
from typing import Any
from uuid import uuid4
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    SendMessageResponse,
    GetTaskResponse,
    TaskState,
    AgentCard
)
import httpx
import aiohttp

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:10000")

def extract_text_from_part(part) -> str | None:
    """Extract text from A2A Part objects with consistent Part(root=TextPart) structure."""
    if hasattr(part, 'root') and hasattr(part.root, 'text') and part.root.text:
        return part.root.text
    return None

def extract_response_text(task) -> str | None:
    """Extract the first text content from task artifacts."""
    if task and hasattr(task, 'artifacts') and task.artifacts:
        for artifact in task.artifacts:
            if hasattr(artifact, 'parts') and artifact.parts:
                for part in artifact.parts:
                    text = extract_text_from_part(part)
                    if text:
                        return text
    return None

def create_send_message_payload(text: str, task_id: str | None = None, context_id: str | None = None) -> dict[str, Any]:
    """Helper function to create the payload for sending a message."""
    payload: dict[str, Any] = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": uuid4().hex,
        }
    }

    if task_id:
        payload["message"]["taskId"] = task_id

    if context_id:
        payload["message"]["contextId"] = context_id
    return payload

async def run_chess_test(test_name: str, fen: str, validator_func) -> None:
    """
    Common function to run a chess test with A2A client.
    
    Args:
        test_name: Display name for the test
        fen: FEN string to test
        validator_func: Function to validate the response
    """
    print(f"\n🧪 Testing {test_name}")
    print("=" * 40)
    
    # Create A2A client with longer timeout for chess analysis
    timeout = httpx.Timeout(60.0)  # 60 seconds for chess analysis
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=AGENT_URL)
        
        # Fetch agent card
        agent_card = await resolver.get_agent_card()
        
        # Initialize A2AClient
        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
        
        prompt = f"Generate best move for FEN: {fen}"
        print(f"📋 Testing position: {fen}")
        print(f"💬 Prompt: {prompt}")
        
        try:
            # Create message payload
            payload = create_send_message_payload(text=prompt)
            
            # Send request
            print("📤 Sending request...")
            response = await client.send_message(
                SendMessageRequest(
                    id=str(uuid4()), 
                    params=MessageSendParams(**payload)
                )
            )
            
            # Extract response
            if hasattr(response, 'root') and hasattr(response.root, 'result'):
                task = response.root.result
            else:
                task = response
            
            result = extract_response_text(task)
            
            # Validate the response using the provided validator
            validator_func(result)
            
        except Exception as e:
            print(f"❌ Error: {e}")

def validate_chess_move(result: str | None) -> None:
    """Validator for chess move responses."""
    if result:
        print(f"♟️  Chess move: {result}")
        
        # Validate UCI format
        if len(result) >= 4 and len(result) <= 5:
            print("✅ Valid UCI format")
        else:
            print("❌ Invalid UCI format")
    else:
        print("❌ No move found in artifacts")

def validate_error_response(result: str | None) -> None:
    """Validator for error responses."""
    if result:
        print(f"📝 Response: {result}")
        
        if "error" in result.lower() or "invalid" in result.lower():
            print("✅ Error handling working correctly")
        else:
            print("❌ Expected error message")
    else:
        print("❌ No response found in artifacts")

async def test_chess_move_generation():
    """Test basic chess move generation."""
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    await run_chess_test("Chess Move Generation", fen, validate_chess_move)

async def test_tactical_position():
    """Test a more complex tactical position."""
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 1"
    await run_chess_test("Tactical Position", fen, validate_chess_move)

async def test_invalid_fen():
    """Test error handling with invalid FEN."""
    fen = "invalid_fen_string"
    await run_chess_test("Invalid FEN", fen, validate_error_response)

async def test_agent_discovery():
    """Test A2A agent discovery endpoint."""
    print("\n🧪 Testing Agent Discovery")
    print("=" * 40)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:10000/.well-known/agent.json") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Agent discovery working")
                    print(f"📋 Agent name: {data.get('name', 'Unknown')}")
                    print(f"📝 Description: {data.get('description', 'No description')}")
                    print(f"🔗 URL: {data.get('url', 'No URL')}")
                else:
                    print(f"❌ Agent discovery failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error testing discovery: {e}")

async def main():
    """Run all tests."""
    print("🚀 A2A Chess Player Agent Test Suite")
    print("=" * 50)
    
    # Test agent discovery first
    await test_agent_discovery()
    
    # Test chess functionality
    await test_chess_move_generation()
    await test_tactical_position()
    await test_invalid_fen()
    
    print("\n" + "=" * 50)
    print("✅ Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main())