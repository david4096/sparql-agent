# CI/CD Pipeline Documentation

This directory contains the comprehensive CI/CD pipeline for the SPARQL Agent project, implementing automated testing, building, deployment, and security scanning across multiple cloud providers.

## Overview

The CI/CD pipeline consists of 5 main workflows:

1. **Test Suite** (`test.yml`) - Comprehensive testing across multiple Python versions and environments
2. **Build and Publish** (`build.yml`) - Build and publish Python packages and Docker images
3. **Deploy** (`deploy.yml`) - Multi-cloud deployment automation
4. **Security Scanning** (`security.yml`) - Comprehensive security and vulnerability scanning
5. **Documentation** (`docs.yml`) - Documentation building and deployment

## Workflows

### 1. Test Suite (test.yml)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests
- Daily scheduled runs at 2 AM UTC
- Manual dispatch

**Features:**
- Quick validation (formatting, linting, type checking)
- Matrix testing across Python 3.9, 3.10, 3.11, 3.12
- Multi-OS testing (Ubuntu, macOS, Windows)
- Integration tests with real SPARQL endpoints
- Performance benchmarking
- Coverage reporting (90% threshold)
- Parallel test execution

**Key Jobs:**
- `quick-check` - Fast validation before full test suite
- `test-matrix` - Cross-platform and cross-version testing
- `integration-tests` - Tests with Blazegraph service
- `performance-tests` - Benchmark tracking
- `coverage-report` - Coverage analysis and reporting

### 2. Build and Publish (build.yml)

**Triggers:**
- Push to `main` or `develop` branches
- Tags matching `v*.*.*`
- Pull requests
- Manual dispatch

**Features:**
- Python package building (sdist and wheel)
- Multi-architecture Docker builds (amd64, arm64)
- Image security scanning with Trivy
- Automated publishing to PyPI and TestPyPI
- Docker image publishing to Docker Hub and GHCR
- GitHub Release creation with changelog

**Key Jobs:**
- `build-python` - Build Python packages
- `build-docker` - Multi-arch Docker builds
- `test-docker` - Docker image testing and scanning
- `push-docker` - Push to registries
- `publish-pypi` - Publish to PyPI
- `create-release` - Create GitHub releases

### 3. Deploy (deploy.yml)

**Triggers:**
- Push to `main` or `develop` branches
- Tags matching `v*.*.*`
- Manual dispatch with environment selection

**Features:**
- Multi-cloud deployment (AWS, GCP, Azure)
- Kubernetes deployment support
- Environment-based deployment (dev, staging, production)
- Pre-deployment backups
- Health checks and verification
- Automatic rollback on failure
- Post-deployment smoke tests

**Key Jobs:**
- `prepare-deployment` - Determine deployment targets
- `deploy-aws` - Deploy to AWS ECS Fargate
- `deploy-gcp` - Deploy to Google Cloud Run
- `deploy-azure` - Deploy to Azure Container Instances
- `deploy-kubernetes` - Deploy to Kubernetes cluster
- `run-migrations` - Database migrations
- `post-deployment-tests` - Verify deployment
- `verify-deployment` - Final verification
- `rollback` - Automatic rollback on failure

### 4. Security Scanning (security.yml)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests
- Daily scheduled runs at 3 AM UTC
- Manual dispatch

**Features:**
- CodeQL analysis for code quality and security
- Dependency vulnerability scanning (Dependabot, Safety, pip-audit)
- Secret scanning (Gitleaks, TruffleHog)
- Container vulnerability scanning (Trivy, Grype)
- SAST scanning (Semgrep, Bandit)
- License compliance checking
- SBOM generation (CycloneDX, SPDX)
- Infrastructure as Code scanning (Checkov)
- Dockerfile best practices (Hadolint)

**Key Jobs:**
- `codeql` - Code analysis
- `bandit` - Python security scanning
- `safety` / `pip-audit` - Dependency vulnerabilities
- `gitleaks` / `trufflehog` - Secret detection
- `trivy` / `grype` - Container scanning
- `semgrep` - SAST analysis
- `license-check` - License compliance
- `sbom` - Software Bill of Materials
- `hadolint` / `checkov` - IaC scanning

### 5. Documentation (docs.yml)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests affecting documentation
- Release publication
- Manual dispatch

**Features:**
- MkDocs documentation building
- API reference generation (pdoc, Sphinx)
- Documentation quality checks
- Link validation
- Spell checking
- Coverage documentation
- Changelog generation
- GitHub Pages deployment
- Versioned documentation for releases

**Key Jobs:**
- `build-docs` - Build MkDocs site
- `deploy-pages` - Deploy to GitHub Pages
- `api-docs` - Generate API documentation
- `docs-quality` - Quality checks
- `coverage-docs` - Coverage reports
- `changelog` - Auto-generate changelog
- `deploy-versioned` - Versioned docs for releases

## Deployment Scripts

Located in `/scripts/`:

### Core Scripts

1. **deploy.sh** - Main deployment script
   ```bash
   ./scripts/deploy.sh <provider> --environment <env> --version <ver>
   ```
   - Supports: AWS, GCP, Azure, Kubernetes
   - Pre-deployment validation
   - Backup creation
   - Health checks

2. **health-check.sh** - Post-deployment verification
   ```bash
   ./scripts/health-check.sh --url <url> --retries 5 --interval 30
   ```
   - Comprehensive health checks
   - API endpoint validation
   - Performance verification
   - Dependency checks

3. **backup.sh** - Backup configuration and data
   ```bash
   ./scripts/backup.sh --environment <env> --provider <provider>
   ```
   - Configuration backup
   - Database backup
   - Cloud storage upload
   - Retention management

4. **rollback.sh** - Rollback failed deployments
   ```bash
   ./scripts/rollback.sh --environment <env> --provider <provider>
   ```
   - Provider-specific rollback
   - Health verification
   - Automated recovery

### Utility Scripts

- **setup-env.sh** - Environment setup and configuration
- **verify-deployment.sh** - Deployment status verification
- **notify-deployment.sh** - Deployment notifications (Slack, email)

## Infrastructure as Code

Located in `/infrastructure/`:

### AWS (aws/ecs-fargate.tf)
- ECS Fargate cluster
- Application Load Balancer
- Auto-scaling configuration
- CloudWatch logging
- IAM roles and policies

### GCP (gcp/cloud-run.tf)
- Cloud Run service
- Auto-scaling
- Service account
- Optional Cloud SQL
- VPC networking

### Azure (azure/container-instances.tf)
- Container Instances
- Resource groups
- Health probes
- DNS configuration

### Kubernetes (kubernetes/deployment.yaml)
- Deployment with 3 replicas
- Service (LoadBalancer)
- ConfigMap and Secrets
- HorizontalPodAutoscaler
- PodDisruptionBudget
- Ingress with TLS

## Configuration Files

- **.github/codeql-config.yml** - CodeQL analysis configuration
- **.github/dependabot.yml** - Automated dependency updates
- **.github/markdown-link-check-config.json** - Link validation config
- **.github/spellcheck-config.yml** - Spell checking configuration
- **cliff.toml** - Changelog generation configuration

## Secrets Required

### GitHub Secrets

**Docker Hub:**
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

**AWS:**
- `AWS_ROLE_ARN`
- `AWS_REGION`

**GCP:**
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `GCP_PROJECT`

**Azure:**
- `AZURE_CREDENTIALS`
- `AZURE_REGISTRY_NAME`
- `AZURE_LOCATION`

**Kubernetes:**
- `KUBE_CONFIG`

**Notifications:**
- `SLACK_WEBHOOK_URL`
- `NOTIFICATION_EMAIL`

**Security:**
- `CODECOV_TOKEN`
- `GITLEAKS_LICENSE`

## Environment Variables

### Application Settings
- `SPARQL_AGENT_HOST` - Service host (default: 0.0.0.0)
- `SPARQL_AGENT_PORT` - Service port (default: 8000)
- `SPARQL_AGENT_LOG_LEVEL` - Logging level
- `SPARQL_AGENT_WORKERS` - Number of workers
- `SPARQL_AGENT_CACHE_DIR` - Cache directory
- `SPARQL_AGENT_DATA_DIR` - Data directory

### Provider Settings
- `AWS_REGION` - AWS deployment region
- `GCP_REGION` - GCP deployment region
- `GCP_PROJECT` - GCP project ID
- `AZURE_LOCATION` - Azure region

## Usage Examples

### Deploy to Production
```bash
# AWS
./scripts/deploy.sh aws --environment production --version v1.0.0

# GCP
./scripts/deploy.sh gcp --environment production --image ghcr.io/user/sparql-agent:v1.0.0

# Kubernetes
./scripts/deploy.sh kubernetes --environment production --version v1.0.0
```

### Run Health Checks
```bash
./scripts/health-check.sh --url https://api.example.com --retries 10
```

### Create Backup
```bash
./scripts/backup.sh --environment production --provider aws
```

### Rollback Deployment
```bash
./scripts/rollback.sh --environment production --provider aws --yes
```

## Quality Gates

The CI/CD pipeline enforces the following quality gates:

1. **Code Quality**
   - Black formatting
   - isort import sorting
   - Ruff linting
   - mypy type checking

2. **Testing**
   - 90% test coverage minimum
   - All unit tests passing
   - Integration tests passing
   - Performance benchmarks

3. **Security**
   - No critical vulnerabilities
   - No secrets in code
   - License compliance
   - Container security

4. **Documentation**
   - Documentation builds successfully
   - No broken links
   - API documentation complete

## Monitoring and Observability

The pipeline integrates with:

- **GitHub Actions** - Workflow execution and logs
- **Codecov** - Coverage tracking
- **GitHub Security** - Security alerts and SARIF reports
- **Docker Hub / GHCR** - Container registry
- **PyPI** - Package distribution
- **GitHub Pages** - Documentation hosting

## Best Practices

1. **Branch Protection**
   - Require PR reviews
   - Require status checks to pass
   - Require branch to be up to date
   - Require linear history

2. **Deployment Strategy**
   - Blue-green deployments
   - Rolling updates with zero downtime
   - Automatic rollback on failure
   - Health checks before traffic routing

3. **Security**
   - Principle of least privilege
   - Regular security scans
   - Automated dependency updates
   - Secret rotation

4. **Monitoring**
   - Health check endpoints
   - Metrics collection
   - Log aggregation
   - Error tracking

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check dependency versions in `uv.lock`
   - Verify Python version compatibility
   - Review build logs in GitHub Actions

2. **Test Failures**
   - Check for flaky tests
   - Verify test environment setup
   - Review coverage reports

3. **Deployment Failures**
   - Check cloud provider credentials
   - Verify infrastructure configuration
   - Review deployment logs
   - Check health check results

4. **Security Alerts**
   - Review security scan results
   - Update vulnerable dependencies
   - Address code quality issues
   - Rotate compromised secrets

## Contributing

When contributing to the CI/CD pipeline:

1. Test changes in a feature branch
2. Use conventional commit messages
3. Update documentation
4. Add tests for new features
5. Ensure all checks pass

## Support

For issues or questions:
- GitHub Issues: https://github.com/david4096/sparql-agent/issues
- Documentation: https://david4096.github.io/sparql-agent/
