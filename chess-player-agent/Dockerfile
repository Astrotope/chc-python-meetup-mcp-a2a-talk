# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .python-version uv.lock ./
COPY chess_player_agent.py ./

# Install dependencies
RUN uv sync --frozen

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AGENT_PORT=5001
ENV CHESS_MCP_SERVER_URL=http://chess-mcp-server:5000/mcp

# Expose port for A2A server
EXPOSE 5001

# Health check for container orchestration
#HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
#    CMD python -c "import asyncio; from chess_player_agent import ChessPlayerAgent; agent = ChessPlayerAgent(); print('healthy')" || exit 1

# Expose the port where Uvicorn will run
EXPOSE ${PORT:-5001}

# Run the chess player agent as A2A server
#CMD ["uv", "run", "python", "-c", "import asyncio; from chess_player_agent import create_app; asyncio.run(create_app())"]
CMD ["uv", "run", "uvicorn", "chess_player_agent:app", "--host", "0.0.0.0", "--port", "5001"]
