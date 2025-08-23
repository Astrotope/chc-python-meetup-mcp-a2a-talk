"""
Simple A2A test using the exact example from FastA2A documentation.
"""
from dotenv import load_dotenv
from pydantic_ai import Agent

# Load environment variables
load_dotenv("./.env")

agent = Agent('openai:gpt-4o', instructions='Be fun!')
app = agent.to_a2a()

if __name__ == "__main__":
    import uvicorn

    print("Starting simple A2A test server on localhost:5002")
    uvicorn.run(app, host="0.0.0.0", port=5002)
