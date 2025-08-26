# White Player Agent Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY white_player_agent/ ./white_player_agent/
COPY chess_game_manager.py ./

# Install dependencies
RUN uv sync --no-dev

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8005/.well-known/agent-card.json || exit 1

# Start the white player agent
CMD ["uv", "run", "uvicorn", "white_player_agent.agent:a2a_app", "--host", "0.0.0.0", "--port", "8005"]