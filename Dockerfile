# Multi-stage Dockerfile for SPARQL Agent
# Optimized for production with UV package manager, security, and caching

# =============================================================================
# Stage 1: Builder - Install dependencies and build application
# =============================================================================
FROM python:3.14-slim AS builder

# Set build arguments
ARG UV_VERSION=0.1.0
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_CACHE_DIR=/root/.cache/uv

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Create application directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install dependencies using UV (production only, no dev dependencies)
# UV creates a virtual environment and installs dependencies efficiently
RUN uv sync --frozen --no-dev

# Copy application source code
COPY src/ ./src/
COPY tests/ ./tests/

# Install the application itself
RUN uv pip install --no-cache-dir -e .

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.14-slim AS runtime

# Set runtime arguments
ARG VERSION=0.1.0
ARG BUILD_DATE
ARG VCS_REF

# Add metadata labels
LABEL maintainer="david@example.com" \
      org.opencontainers.image.title="SPARQL Agent" \
      org.opencontainers.image.description="Intelligent SPARQL query agent with OWL ontology support and LLM integration" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/yourusername/sparql-agent" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="SPARQL Agent" \
      org.opencontainers.image.licenses="MIT"

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r sparql --gid=1000 && \
    useradd -r -g sparql --uid=1000 --home-dir=/app --shell=/sbin/nologin sparql

# Create application directories with proper permissions
WORKDIR /app
RUN mkdir -p /app/logs /app/data /app/.cache && \
    chown -R sparql:sparql /app

# Copy Python environment from builder
COPY --from=builder --chown=sparql:sparql /app/.venv /app/.venv
COPY --from=builder --chown=sparql:sparql /app/src /app/src
COPY --from=builder --chown=sparql:sparql /app/pyproject.toml /app/

# Set environment variables for runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    # Application settings
    SPARQL_AGENT_HOST=0.0.0.0 \
    SPARQL_AGENT_PORT=8000 \
    SPARQL_AGENT_LOG_LEVEL=INFO \
    SPARQL_AGENT_WORKERS=4 \
    # Cache and data directories
    SPARQL_AGENT_CACHE_DIR=/app/.cache \
    SPARQL_AGENT_DATA_DIR=/app/data \
    SPARQL_AGENT_LOG_DIR=/app/logs

# Copy entrypoint and health check scripts
COPY --chown=sparql:sparql docker/entrypoint.sh /app/entrypoint.sh
COPY --chown=sparql:sparql docker/healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh

# Switch to non-root user
USER sparql

# Expose ports
# 8000: FastAPI web server
# 3000: MCP server
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/app/healthcheck.sh"]

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: run web server
CMD ["web"]

# =============================================================================
# Stage 3: Development image with dev dependencies and tools
# =============================================================================
FROM runtime AS development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy UV from builder
COPY --from=builder /root/.cargo/bin/uv /usr/local/bin/uv

# Install development dependencies
COPY --chown=sparql:sparql pyproject.toml uv.lock ./
RUN uv sync --frozen

# Switch back to non-root user
USER sparql

# Override for development - enable reload
ENV SPARQL_AGENT_RELOAD=true \
    SPARQL_AGENT_LOG_LEVEL=DEBUG

# Development command with hot reload
CMD ["uvicorn", "sparql_agent.web.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Stage 4: Testing image with test dependencies
# =============================================================================
FROM development AS testing

USER root

# Install additional test dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy test files
COPY --chown=sparql:sparql tests/ /app/tests/
COPY --chown=sparql:sparql pytest.ini /app/

USER sparql

# Run tests by default
CMD ["pytest", "-v", "--cov=sparql_agent", "--cov-report=html", "--cov-report=term"]

# =============================================================================
# Stage 5: MCP Server image (specialized for MCP protocol)
# =============================================================================
FROM runtime AS mcp-server

# Override default command to run MCP server
ENV SPARQL_AGENT_MODE=mcp \
    SPARQL_AGENT_PORT=3000

EXPOSE 3000

CMD ["mcp"]

# =============================================================================
# Build instructions:
#
# Build production image:
#   docker build -t sparql-agent:latest .
#
# Build development image:
#   docker build --target development -t sparql-agent:dev .
#
# Build testing image:
#   docker build --target testing -t sparql-agent:test .
#
# Build MCP server:
#   docker build --target mcp-server -t sparql-agent:mcp .
#
# Multi-arch build:
#   docker buildx build --platform linux/amd64,linux/arm64 -t sparql-agent:latest .
#
# With build args:
#   docker build \
#     --build-arg VERSION=1.0.0 \
#     --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#     --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#     -t sparql-agent:1.0.0 .
# =============================================================================
