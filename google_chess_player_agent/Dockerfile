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
COPY __init__.py agent.py agent_executor.py a2a_chess_player_agent_server.py ./

# Install dependencies
RUN uv sync --frozen

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AGENT_PORT=10000
ENV CHESS_MCP_SERVER_URL=http://chess-mcp-server:5000/mcp

# Expose port for A2A server
EXPOSE 10000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:10000/.well-known/agent.json || exit 1

# Run the Google A2A chess player agent server
CMD ["uv", "run", "python", "a2a_chess_player_agent_server.py", "--host", "0.0.0.0", "--port", "10000"]