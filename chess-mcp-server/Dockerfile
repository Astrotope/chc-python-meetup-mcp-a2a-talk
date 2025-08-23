# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    stockfish \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .python-version uv.lock ./
COPY chess_mcp_server.py ./

# Install dependencies
RUN uv sync --frozen

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STOCKFISH_PATH="/usr/games/stockfish"

# Expose port for MCP server
EXPOSE 8003

# Run the chess MCP server using fastmcp
CMD ["uv", "run", "fastmcp", "run", "chess_mcp_server.py", "--transport", "streamable-http", "--port", "5000", "--host", "0.0.0.0"]
