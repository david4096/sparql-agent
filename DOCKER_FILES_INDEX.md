# Docker Files Index

Complete index of all Docker-related files in the SPARQL Agent project.

## Quick Navigation

- [Core Files](#core-files)
- [Orchestration](#orchestration)
- [Scripts](#scripts)
- [Configuration](#configuration)
- [Kubernetes](#kubernetes)
- [CI/CD](#cicd)
- [Documentation](#documentation)

## Core Files

### Dockerfile
**Location**: `/Dockerfile`
**Purpose**: Multi-stage Docker image build configuration
**Stages**: builder, runtime, development, testing, mcp-server
**Size**: ~200 lines

### .dockerignore
**Location**: `/.dockerignore`
**Purpose**: Exclude files from Docker build context
**Optimizes**: Build speed and image size

## Orchestration

### docker-compose.yml
**Location**: `/docker-compose.yml`
**Purpose**: Production stack orchestration
**Services**: 
- sparql-agent-api (API server)
- sparql-agent-mcp (MCP server)
- redis (cache)
- nginx (proxy)
- prometheus (metrics, optional)
- grafana (visualization, optional)

### docker-compose.dev.yml
**Location**: `/docker-compose.dev.yml`
**Purpose**: Development environment
**Services**:
- sparql-agent-api (with hot reload)
- sparql-agent-mcp
- redis
- redis-commander (GUI)
- jupyter (notebooks)
- test-runner (continuous testing)
- postgres (database)
- adminer (DB GUI)
- mailhog (email testing)

## Scripts

### docker/entrypoint.sh
**Location**: `/docker/entrypoint.sh`
**Purpose**: Container initialization and service startup
**Modes**: web, mcp, cli, test, shell

### docker/healthcheck.sh
**Location**: `/docker/healthcheck.sh`
**Purpose**: Health check for container orchestration
**Checks**: HTTP endpoints and process status

### docker/build.sh
**Location**: `/docker/build.sh`
**Purpose**: Advanced Docker build automation
**Features**: Multi-arch, caching, tagging, registry push

### docker/run.sh
**Location**: `/docker/run.sh`
**Purpose**: Convenient container execution
**Modes**: web, mcp, cli with various options

### docker/dev.sh
**Location**: `/docker/dev.sh`
**Purpose**: Development environment management
**Commands**: up, down, logs, shell, test, clean

## Configuration

### Nginx

#### docker/nginx/nginx.conf
**Location**: `/docker/nginx/nginx.conf`
**Purpose**: Main Nginx configuration
**Features**: Performance tuning, logging, rate limiting

#### docker/nginx/conf.d/sparql-agent.conf
**Location**: `/docker/nginx/conf.d/sparql-agent.conf`
**Purpose**: SPARQL Agent routing and proxy configuration
**Features**: API routing, WebSocket support, SSL/TLS template

### Environment

#### .env.example
**Location**: `/.env.example`
**Purpose**: Environment variable template
**Contains**: All configuration options with descriptions

## Kubernetes

### k8s/namespace.yaml
**Location**: `/k8s/namespace.yaml`
**Purpose**: Create isolated namespace for SPARQL Agent

### k8s/configmap.yaml
**Location**: `/k8s/configmap.yaml`
**Purpose**: Non-sensitive application configuration

### k8s/secret.yaml
**Location**: `/k8s/secret.yaml`
**Purpose**: Sensitive data (API keys, passwords)
**Note**: Template only, customize for your environment

### k8s/deployment.yaml
**Location**: `/k8s/deployment.yaml`
**Purpose**: Define deployments for API, MCP, and Redis
**Replicas**: API (3), MCP (2), Redis (1)

### k8s/service.yaml
**Location**: `/k8s/service.yaml`
**Purpose**: Service definitions for pod discovery

### k8s/ingress.yaml
**Location**: `/k8s/ingress.yaml`
**Purpose**: External access with TLS/SSL
**Features**: Rate limiting, CORS, SSL/TLS

### k8s/hpa.yaml
**Location**: `/k8s/hpa.yaml`
**Purpose**: Horizontal Pod Autoscaling configuration
**Metrics**: CPU and memory-based scaling

### k8s/pvc.yaml
**Location**: `/k8s/pvc.yaml`
**Purpose**: Persistent volume claims for Redis and data

### k8s/serviceaccount.yaml
**Location**: `/k8s/serviceaccount.yaml`
**Purpose**: RBAC configuration and permissions

## CI/CD

### .github/workflows/docker-build-push.yml
**Location**: `/.github/workflows/docker-build-push.yml`
**Purpose**: Automated Docker builds and deployments
**Triggers**: Push, PR, manual
**Features**:
- Multi-arch builds
- Security scanning
- Testing
- Registry push
- Image signing
- Deployment

## Documentation

### DOCKER.md
**Location**: `/DOCKER.md`
**Purpose**: Comprehensive Docker deployment guide
**Sections**:
- Quick start
- Building images
- Running containers
- Docker Compose usage
- Kubernetes deployment
- Configuration reference
- Security best practices
- Monitoring
- Troubleshooting

### DOCKER_QUICKSTART.md
**Location**: `/DOCKER_QUICKSTART.md`
**Purpose**: 5-minute quick start guide
**Methods**: 4 different ways to get started quickly

### DOCKER_CONTAINERIZATION_COMPLETE.md
**Location**: `/DOCKER_CONTAINERIZATION_COMPLETE.md`
**Purpose**: Implementation summary and architecture
**Contains**: Complete overview of all components

### Makefile
**Location**: `/Makefile`
**Purpose**: Convenient command shortcuts
**Targets**: 50+ commands for common tasks
**Categories**: Build, run, test, deploy, clean, etc.

## Helper Files

### README.md
**Location**: `/README.md`
**Includes**: Docker deployment section

## File Tree

```
sparql-agent/
├── Dockerfile
├── .dockerignore
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── Makefile
│
├── DOCKER.md
├── DOCKER_QUICKSTART.md
├── DOCKER_CONTAINERIZATION_COMPLETE.md
├── DOCKER_FILES_INDEX.md
│
├── docker/
│   ├── entrypoint.sh
│   ├── healthcheck.sh
│   ├── build.sh
│   ├── run.sh
│   ├── dev.sh
│   │
│   └── nginx/
│       ├── nginx.conf
│       └── conf.d/
│           └── sparql-agent.conf
│
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pvc.yaml
│   └── serviceaccount.yaml
│
└── .github/
    └── workflows/
        └── docker-build-push.yml
```

## Quick Access

### Start Here
1. [DOCKER_QUICKSTART.md](./DOCKER_QUICKSTART.md) - Get running in 5 minutes
2. [Makefile](./Makefile) - See all available commands (`make help`)
3. [.env.example](./.env.example) - Configure your environment

### Deep Dive
1. [DOCKER.md](./DOCKER.md) - Complete deployment guide
2. [Dockerfile](./Dockerfile) - Understand the build process
3. [docker-compose.yml](./docker-compose.yml) - Production stack
4. [k8s/](./k8s/) - Kubernetes deployment

### Development
1. [docker-compose.dev.yml](./docker-compose.dev.yml) - Dev environment
2. [docker/dev.sh](./docker/dev.sh) - Dev helper script
3. [Makefile](./Makefile) - `make dev-up`

## Commands Quick Reference

```bash
# Quick start
make quick-start

# Development
make dev-up
make dev-logs
make dev-test
make dev-shell

# Building
make build
make build-dev
make build-all

# Testing
make test
make test-coverage

# Kubernetes
make k8s-deploy
make k8s-status
make k8s-logs

# Utilities
make logs
make shell
make health
make clean

# Help
make help
```

## File Sizes

| File | Size | Type |
|------|------|------|
| Dockerfile | ~7 KB | Build config |
| .dockerignore | ~3 KB | Build optimization |
| docker-compose.yml | ~8 KB | Orchestration |
| docker-compose.dev.yml | ~12 KB | Dev orchestration |
| docker/entrypoint.sh | ~5 KB | Init script |
| docker/build.sh | ~10 KB | Build automation |
| DOCKER.md | ~50 KB | Documentation |
| Makefile | ~10 KB | Automation |

## Maintenance

### Regular Tasks
- Update base images
- Review security scans
- Update dependencies
- Test new Docker/K8s versions
- Update documentation

### Version Updates
When updating SPARQL Agent version:
1. Update `VERSION` in .env.example
2. Tag Docker images with new version
3. Update Kubernetes manifests
4. Update documentation

## Support

For questions about Docker files:
- Check [DOCKER.md](./DOCKER.md) first
- See [DOCKER_QUICKSTART.md](./DOCKER_QUICKSTART.md) for quick help
- GitHub Issues for problems
- Email for support

---

**Last Updated**: October 2024
**Version**: 1.0.0
