#!/usr/bin/env python3
import asyncio
import httpx
from a2a.client import ClientFactory, ClientConfig, A2ACardResolver
from a2a.types import TransportProtocol

async def check_client_interface():
    async with httpx.AsyncClient() as httpx_client:
        try:
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url='http://localhost:10000')
            agent_card = await resolver.get_agent_card()
            
            config = ClientConfig(
                httpx_client=httpx_client,
                supported_transports=[TransportProtocol.jsonrpc],
                streaming=False
            )
            factory = ClientFactory(config)
            client = factory.create(agent_card)
            
            print('Client type:', type(client))
            print('Client methods:', [x for x in dir(client) if not x.startswith('_')])
            
            # Check if it has send_message
            if hasattr(client, 'send_message'):
                print('send_message type:', type(client.send_message))
                import inspect
                print('send_message signature:', inspect.signature(client.send_message))
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_client_interface())