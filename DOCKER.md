# Docker Deployment Guide for SPARQL Agent

Comprehensive guide for containerizing and deploying SPARQL Agent with Docker, Docker Compose, and Kubernetes.

## Table of Contents

- [Quick Start](#quick-start)
- [Docker Images](#docker-images)
- [Building Images](#building-images)
- [Running Containers](#running-containers)
- [Docker Compose](#docker-compose)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration](#configuration)
- [Security](#security)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB free disk space

### Fastest Start (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/david4096/sparql-agent.git
cd sparql-agent

# 2. Create environment file
cp .env.example .env
# Edit .env and add your API keys

# 3. Start all services
docker-compose up -d

# 4. Check health
curl http://localhost:8000/health

# 5. Access API documentation
open http://localhost:8000/docs
```

### Quick Test (Single Container)

```bash
# Pull latest image
docker pull sparql-agent:latest

# Run container
docker run -d \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your-key \
  --name sparql-agent \
  sparql-agent:latest

# View logs
docker logs -f sparql-agent
```

## Docker Images

### Available Images

We provide multiple specialized images for different use cases:

| Image | Target | Description | Size |
|-------|--------|-------------|------|
| `sparql-agent:latest` | runtime | Production API server | ~500MB |
| `sparql-agent:dev` | development | Development with hot reload | ~700MB |
| `sparql-agent:test` | testing | Testing environment | ~700MB |
| `sparql-agent:mcp` | mcp-server | MCP protocol server | ~500MB |

### Image Variants

```bash
# Production runtime
sparql-agent:latest
sparql-agent:1.0.0

# Development
sparql-agent:dev
sparql-agent:1.0.0-dev

# MCP Server
sparql-agent:mcp
sparql-agent:1.0.0-mcp

# Specific version
sparql-agent:1.2.3
```

### Multi-Architecture Support

All images support multiple architectures:
- `linux/amd64` (x86_64)
- `linux/arm64` (aarch64, Apple Silicon)

Docker automatically pulls the correct architecture for your platform.

## Building Images

### Using Build Script (Recommended)

```bash
# Build production image
./docker/build.sh -t runtime -v 1.0.0

# Build development image
./docker/build.sh -t development

# Build MCP server
./docker/build.sh -t mcp-server

# Build and push to registry
./docker/build.sh -t runtime --push -r myregistry.com

# Build multi-architecture
./docker/build.sh -t runtime --platform linux/amd64,linux/arm64

# Build with cache
./docker/build.sh --cache-from myregistry.com/sparql-agent:latest
```

### Manual Build

```bash
# Build production image
docker build -t sparql-agent:latest .

# Build development image
docker build --target development -t sparql-agent:dev .

# Build MCP server
docker build --target mcp-server -t sparql-agent:mcp .

# Build with build arguments
docker build \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  -t sparql-agent:1.0.0 .

# Multi-platform build
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t myregistry.com/sparql-agent:latest .
```

## Running Containers

### Using Run Script (Recommended)

```bash
# Run web server
./docker/run.sh --mode web --port 8000

# Run MCP server
./docker/run.sh --mode mcp --port 3000

# Run interactive CLI
./docker/run.sh --mode cli --fg

# Run with environment file
./docker/run.sh --env-file .env

# Run with custom configuration
./docker/run.sh \
  --env ANTHROPIC_API_KEY=sk-ant-xxx \
  --volume ./data:/app/data \
  --debug
```

### Manual Run

#### Web Server

```bash
docker run -d \
  --name sparql-agent-api \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your-key \
  -e OPENAI_API_KEY=your-key \
  -e SPARQL_AGENT_LOG_LEVEL=INFO \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  sparql-agent:latest web
```

#### MCP Server

```bash
docker run -d \
  --name sparql-agent-mcp \
  -p 3000:3000 \
  -e ANTHROPIC_API_KEY=your-key \
  sparql-agent:mcp mcp
```

#### Interactive CLI

```bash
docker run -it --rm \
  -e ANTHROPIC_API_KEY=your-key \
  sparql-agent:latest cli
```

#### Run Tests

```bash
docker run --rm \
  -v $(pwd)/htmlcov:/app/htmlcov \
  sparql-agent:test
```

## Docker Compose

### Production Stack

Start complete production stack with API, MCP server, Redis, and Nginx:

```bash
# Start all services
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f sparql-agent-api

# Scale API servers
docker-compose up -d --scale sparql-agent-api=3

# Stop services
docker-compose down

# Clean up (including volumes)
docker-compose down -v
```

### Development Stack

```bash
# Using dev script (recommended)
./docker/dev.sh up

# Or directly with docker-compose
docker-compose -f docker-compose.dev.yml up -d

# With all development tools
./docker/dev.sh up --profile tools --profile jupyter

# View logs
./docker/dev.sh logs -f

# Run tests
./docker/dev.sh test

# Open shell
./docker/dev.sh shell

# Clean up
./docker/dev.sh clean
```

### Available Services

#### Production (`docker-compose.yml`)

- `sparql-agent-api` - FastAPI web server (port 8000)
- `sparql-agent-mcp` - MCP server (port 3000)
- `redis` - Cache layer (port 6379)
- `nginx` - Reverse proxy (ports 80, 443)
- `prometheus` - Metrics (port 9090, profile: monitoring)
- `grafana` - Dashboards (port 3001, profile: monitoring)

#### Development (`docker-compose.dev.yml`)

- `sparql-agent-api` - API with hot reload (port 8000)
- `sparql-agent-mcp` - MCP server (port 3000)
- `redis` - Cache (port 6379)
- `redis-commander` - Redis GUI (port 8081, profile: tools)
- `jupyter` - Jupyter Lab (port 8888, profile: jupyter)
- `test-runner` - Continuous testing (profile: testing)
- `postgres` - Database (port 5432, profile: database)
- `adminer` - DB GUI (port 8082, profile: database)
- `mailhog` - Email testing (ports 1025, 8025, profile: tools)

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Ingress controller installed (nginx-ingress recommended)
- cert-manager for SSL (optional)

### Quick Deploy

```bash
# Apply all manifests
kubectl apply -f k8s/

# Or step by step
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Check deployment
kubectl get pods -n sparql-agent
kubectl get svc -n sparql-agent

# View logs
kubectl logs -f deployment/sparql-agent-api -n sparql-agent

# Check health
kubectl port-forward -n sparql-agent svc/sparql-agent-api-service 8000:8000
curl http://localhost:8000/health
```

### Customization

Edit `k8s/configmap.yaml` for configuration:

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sparql-agent-config
  namespace: sparql-agent
data:
  SPARQL_AGENT_LOG_LEVEL: "INFO"
  SPARQL_AGENT_WORKERS: "4"
  # ... add your settings
```

Edit `k8s/secret.yaml` for secrets:

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: sparql-agent-secrets
  namespace: sparql-agent
type: Opaque
stringData:
  ANTHROPIC_API_KEY: "your-key-here"
  OPENAI_API_KEY: "your-key-here"
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment/sparql-agent-api -n sparql-agent --replicas=5

# Auto-scaling is configured via HPA
kubectl get hpa -n sparql-agent

# Adjust HPA limits
kubectl edit hpa/sparql-agent-api-hpa -n sparql-agent
```

### Monitoring

```bash
# Check resource usage
kubectl top pods -n sparql-agent

# Check HPA status
kubectl get hpa -n sparql-agent

# View events
kubectl get events -n sparql-agent --sort-by='.lastTimestamp'
```

## Configuration

### Environment Variables

#### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SPARQL_AGENT_HOST` | `0.0.0.0` | Server host |
| `SPARQL_AGENT_PORT` | `8000` | Server port |
| `SPARQL_AGENT_WORKERS` | `4` | Worker processes |
| `SPARQL_AGENT_LOG_LEVEL` | `INFO` | Log level |
| `SPARQL_AGENT_MODE` | `web` | Run mode (web/mcp/cli) |

#### LLM Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `SPARQL_AGENT_LLM_PROVIDER` | No | LLM provider (anthropic/openai) |
| `SPARQL_AGENT_LLM_MODEL` | No | Model name |

#### Redis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_ENABLED` | `true` | Enable Redis cache |
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |

#### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY_ENABLED` | `false` | Enable API key auth |
| `API_KEY` | - | API key value |
| `CORS_ORIGINS` | `*` | CORS allowed origins |

### Configuration Files

Create `.env` file for local development:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your-key
OPENAI_API_KEY=sk-your-key
SPARQL_AGENT_LOG_LEVEL=DEBUG
REDIS_ENABLED=true
```

## Security

### Best Practices

1. **Never commit secrets** to version control
2. **Use secrets management** in production (Vault, AWS Secrets Manager, etc.)
3. **Enable authentication** with `API_KEY_ENABLED=true`
4. **Restrict CORS** origins in production
5. **Use HTTPS/TLS** in production (configured in Ingress)
6. **Run as non-root** (already configured in Dockerfile)
7. **Scan images** regularly with Trivy or similar tools
8. **Keep images updated** to get security patches

### Security Scanning

```bash
# Scan image with Trivy
trivy image sparql-agent:latest

# Scan for critical and high vulnerabilities
trivy image --severity CRITICAL,HIGH sparql-agent:latest

# Generate report
trivy image --format json --output report.json sparql-agent:latest
```

### Image Signing

```bash
# Sign image with cosign
cosign sign --key cosign.key sparql-agent:latest

# Verify signature
cosign verify --key cosign.pub sparql-agent:latest
```

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/metrics

# Check all services
docker-compose ps
```

### Logs

```bash
# View container logs
docker logs -f sparql-agent-api

# Docker Compose logs
docker-compose logs -f

# Kubernetes logs
kubectl logs -f deployment/sparql-agent-api -n sparql-agent

# Follow logs from multiple containers
docker-compose logs -f sparql-agent-api sparql-agent-mcp
```

### Prometheus Metrics

Access Prometheus at `http://localhost:9090` (when using monitoring profile):

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access Prometheus
open http://localhost:9090

# Access Grafana
open http://localhost:3001
# Default credentials: admin/admin
```

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker logs sparql-agent-api

# Check if port is already in use
lsof -i :8000

# Verify environment variables
docker exec sparql-agent-api env | grep SPARQL
```

#### Redis Connection Issues

```bash
# Check if Redis is running
docker ps | grep redis

# Test Redis connection
docker exec -it redis redis-cli ping

# Check Redis logs
docker logs redis
```

#### Permission Issues

```bash
# Check volume permissions
ls -la data/ logs/

# Fix permissions
sudo chown -R 1000:1000 data/ logs/
```

#### Out of Memory

```bash
# Check container memory usage
docker stats

# Increase memory limit in docker-compose.yml
services:
  sparql-agent-api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Debug Mode

```bash
# Run with debug logging
docker run -it --rm \
  -e SPARQL_AGENT_LOG_LEVEL=DEBUG \
  -e SPARQL_AGENT_DEBUG=true \
  sparql-agent:latest

# Or with Docker Compose
SPARQL_AGENT_LOG_LEVEL=DEBUG docker-compose up
```

### Access Container Shell

```bash
# Docker
docker exec -it sparql-agent-api /bin/sh

# Docker Compose
docker-compose exec sparql-agent-api /bin/sh

# Kubernetes
kubectl exec -it deployment/sparql-agent-api -n sparql-agent -- /bin/sh
```

## Performance Optimization

### Resource Limits

```yaml
# docker-compose.yml
services:
  sparql-agent-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Caching

- Redis is used for query result caching
- Adjust `SPARQL_AGENT_CACHE_TTL` for cache duration
- Monitor Redis memory usage

### Scaling

```bash
# Scale with Docker Compose
docker-compose up -d --scale sparql-agent-api=5

# Scale with Kubernetes
kubectl scale deployment/sparql-agent-api -n sparql-agent --replicas=5
```

## CI/CD Integration

### GitHub Actions

Automated builds and deployments are configured in `.github/workflows/docker-build-push.yml`

Features:
- Multi-architecture builds
- Security scanning with Trivy
- Automated testing
- Container signing with cosign
- Deployment to staging/production

### GitLab CI

Example `.gitlab-ci.yml`:

```yaml
build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

## Additional Resources

- [Dockerfile Reference](./Dockerfile)
- [Docker Compose Files](./docker-compose.yml)
- [Kubernetes Manifests](./k8s/)
- [Build Scripts](./docker/)
- [Main Documentation](./README.md)

## Support

For issues and questions:
- GitHub Issues: https://github.com/david4096/sparql-agent/issues
- Documentation: https://github.com/david4096/sparql-agent
- Email: david@example.com
