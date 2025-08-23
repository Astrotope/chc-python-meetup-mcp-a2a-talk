# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies including Stockfish and curl for uv installation
RUN apt-get update && apt-get install -y \
    stockfish \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy uv files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose Gradio's default port
EXPOSE 7860

# Set environment variables for Gradio
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV STOCKFISH_PATH="/usr/games/stockfish"

# Run the application with uv
CMD ["uv", "run", "gradio_chess_10.py"]