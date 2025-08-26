# Gradio Chess UI Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Cairo for cairosvg
RUN apt-get update && apt-get install -y \
    curl \
    libcairo2-dev \
    libgirepository1.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY simple_chess_ui.py ./
COPY chess_game_manager.py ./
COPY orchestrator_agent/ ./orchestrator_agent/

# Install dependencies
RUN uv sync --no-dev

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port (Gradio default)
EXPOSE 7865

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7865 || exit 1

# Start the Gradio UI
CMD ["uv", "run", "python", "simple_chess_ui.py"]
