# Docker Quick Start Guide

Get SPARQL Agent running in Docker in under 5 minutes!

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- 4GB RAM available
- 10GB free disk space

## Method 1: Docker Compose (Recommended)

This starts the complete stack with API, MCP server, Redis, and Nginx.

```bash
# 1. Clone repository
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent

# 2. Create environment file
cp .env.example .env

# 3. Add your API keys to .env
# Edit .env and add:
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# or
# OPENAI_API_KEY=sk-your-key-here

# 4. Start everything
docker-compose up -d

# 5. Check health
curl http://localhost:8000/health

# 6. Access API docs
open http://localhost:8000/docs
```

That's it! The API is now running at `http://localhost:8000`.

## Method 2: Single Container

For a quick test without the full stack:

```bash
# Pull the latest image
docker pull sparql-agent:latest

# Run with your API key
docker run -d \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-your-key \
  --name sparql-agent \
  sparql-agent:latest

# Check logs
docker logs -f sparql-agent

# Test it
curl http://localhost:8000/health
```

## Method 3: Development Environment

For local development with hot reload:

```bash
# Start development environment
./docker/dev.sh up

# Or with all tools (Redis GUI, Jupyter, etc.)
./docker/dev.sh up --profile tools --profile jupyter

# View logs
./docker/dev.sh logs -f

# Run tests
./docker/dev.sh test

# Open shell
./docker/dev.sh shell
```

## Method 4: Makefile Commands

For the ultimate convenience:

```bash
# Build and run
make quick-start

# Or for development
make dev-up

# View logs
make logs

# Run tests
make test

# Clean up
make clean
```

## Common Tasks

### View Logs

```bash
# Docker Compose
docker-compose logs -f sparql-agent-api

# Single container
docker logs -f sparql-agent

# Development
./docker/dev.sh logs -f
```

### Run Tests

```bash
# Docker Compose
docker-compose run --rm sparql-agent-api pytest

# Development
./docker/dev.sh test

# Makefile
make test
```

### Open Shell

```bash
# Docker Compose
docker-compose exec sparql-agent-api /bin/sh

# Single container
docker exec -it sparql-agent /bin/sh

# Development
./docker/dev.sh shell
```

### Stop Everything

```bash
# Docker Compose
docker-compose down

# Single container
docker stop sparql-agent

# Development
./docker/dev.sh down
```

## Access Points

After starting, access these URLs:

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | Main API |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Health Check | http://localhost:8000/health | Health status |
| MCP Server | http://localhost:3000 | Model Context Protocol |
| Redis Commander | http://localhost:8081 | Redis GUI (dev only) |
| Jupyter Lab | http://localhost:8888 | Jupyter notebooks (dev only) |
| Grafana | http://localhost:3001 | Metrics dashboard (monitoring profile) |

## Environment Variables

Essential environment variables for `.env` file:

```bash
# At least one LLM API key
ANTHROPIC_API_KEY=sk-ant-your-key
OPENAI_API_KEY=sk-your-key

# Optional settings
LOG_LEVEL=INFO
REDIS_ENABLED=true
CACHE_ENABLED=true
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs sparql-agent

# Check if port is in use
lsof -i :8000

# Try a different port
docker run -p 8080:8000 ... sparql-agent:latest
```

### Redis connection error

```bash
# Check if Redis is running
docker ps | grep redis

# Start Redis
docker-compose up -d redis
```

### Out of memory

```bash
# Check memory usage
docker stats

# Increase memory limit
docker run -m 2g ... sparql-agent:latest
```

## Building from Source

```bash
# Build production image
docker build -t sparql-agent:latest .

# Build development image
docker build --target development -t sparql-agent:dev .

# Or use the build script
./docker/build.sh -t runtime

# Or use Makefile
make build
```

## Next Steps

1. Read the [full Docker documentation](./DOCKER.md)
2. Check out [API examples](./README.md#usage)
3. Deploy to [Kubernetes](./k8s/)
4. Set up [monitoring](./docker-compose.yml) with Prometheus/Grafana

## Getting Help

- Documentation: [DOCKER.md](./DOCKER.md)
- Main README: [README.md](./README.md)
- Issues: https://github.com/david4096/sparql-agent/issues
- Email: david@example.com

## Quick Reference Commands

```bash
# Build and run
make quick-start

# Development environment
make dev-up

# Run tests
make test

# View logs
make logs

# Stop all
make down

# Clean up
make clean

# Full help
make help
```

## Done!

You now have SPARQL Agent running in Docker! Visit http://localhost:8000/docs to explore the API.
