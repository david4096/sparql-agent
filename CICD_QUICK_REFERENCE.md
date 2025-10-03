# CI/CD Pipeline Quick Reference

## Workflows

| Workflow | File | Purpose | Trigger |
|----------|------|---------|---------|
| Test Suite | `test.yml` | Run tests, coverage, benchmarks | Push, PR, Daily |
| Build & Publish | `build.yml` | Build packages, Docker images | Push, Tags, PR |
| Deploy | `deploy.yml` | Multi-cloud deployment | Push, Tags, Manual |
| Security | `security.yml` | Security scanning | Push, PR, Daily |
| Documentation | `docs.yml` | Build and deploy docs | Push, PR, Release |

## Scripts Quick Reference

```bash
# Deployment
./scripts/deploy.sh aws --environment production --version v1.0.0
./scripts/deploy.sh gcp --environment staging --image ghcr.io/user/app:latest
./scripts/deploy.sh azure --environment production --version v1.0.0
./scripts/deploy.sh kubernetes --environment production --version v1.0.0

# Health Checks
./scripts/health-check.sh --url https://api.example.com --retries 5 --interval 30

# Backup
./scripts/backup.sh --environment production --provider aws

# Rollback
./scripts/rollback.sh --environment production --provider aws --yes

# Environment Setup
./scripts/setup-env.sh production

# Verify Deployment
./scripts/verify-deployment.sh --environment production --version v1.0.0

# Notify
./scripts/notify-deployment.sh --provider aws --environment prod --version v1.0.0 --status success
```

## Common Commands

### Run Tests Locally
```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=sparql_agent --cov-report=html

# Specific markers
uv run pytest tests/ -m "not integration"

# Parallel execution
uv run pytest tests/ -n auto
```

### Code Quality
```bash
# Format code
uv run black src tests

# Sort imports
uv run isort src tests

# Lint
uv run ruff check src tests

# Type check
uv run mypy src
```

### Build Locally
```bash
# Build Python package
python -m build

# Build Docker image
docker build -t sparql-agent:local .

# Build specific target
docker build --target development -t sparql-agent:dev .
```

### Manual Workflow Trigger
```bash
# Using GitHub CLI
gh workflow run test.yml
gh workflow run build.yml --ref develop
gh workflow run deploy.yml -f environment=staging -f cloud_provider=aws

# Using web interface
# Actions → Select workflow → Run workflow → Select branch/inputs
```

## Infrastructure Deployment

### Terraform (AWS)
```bash
cd infrastructure/aws
terraform init
terraform plan -var="environment=production"
terraform apply -var="environment=production"
```

### Terraform (GCP)
```bash
cd infrastructure/gcp
terraform init
terraform plan -var="gcp_project=my-project" -var="environment=production"
terraform apply
```

### Terraform (Azure)
```bash
cd infrastructure/azure
terraform init
terraform plan -var="environment=production"
terraform apply
```

### Kubernetes
```bash
# Apply manifests
kubectl apply -f infrastructure/kubernetes/deployment.yaml

# Update image
kubectl set image deployment/sparql-agent \
  sparql-agent=ghcr.io/user/sparql-agent:v1.0.0 \
  -n sparql-agent

# Check status
kubectl get pods -n sparql-agent
kubectl rollout status deployment/sparql-agent -n sparql-agent
```

## Environment Variables

### Application
```bash
SPARQL_AGENT_HOST=0.0.0.0
SPARQL_AGENT_PORT=8000
SPARQL_AGENT_LOG_LEVEL=INFO
SPARQL_AGENT_WORKERS=4
SPARQL_AGENT_CACHE_DIR=/app/.cache
SPARQL_AGENT_DATA_DIR=/app/data
```

### Cloud Providers
```bash
# AWS
AWS_REGION=us-east-1
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/sparql-agent

# GCP
GCP_PROJECT=my-project-id
GCP_REGION=us-central1

# Azure
AZURE_LOCATION=eastus
```

## Monitoring URLs

- **GitHub Actions:** `https://github.com/USER/REPO/actions`
- **Codecov:** `https://codecov.io/gh/USER/REPO`
- **Security:** `https://github.com/USER/REPO/security`
- **Documentation:** `https://USER.github.io/REPO`
- **Releases:** `https://github.com/USER/REPO/releases`

## Status Badges

Add to README.md:

```markdown
[![Tests](https://github.com/USER/REPO/workflows/Test%20Suite/badge.svg)](https://github.com/USER/REPO/actions)
[![Build](https://github.com/USER/REPO/workflows/Build%20and%20Publish/badge.svg)](https://github.com/USER/REPO/actions)
[![Security](https://github.com/USER/REPO/workflows/Security%20Scanning/badge.svg)](https://github.com/USER/REPO/actions)
[![codecov](https://codecov.io/gh/USER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USER/REPO)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://USER.github.io/REPO)
```

## Troubleshooting

### Build Failures
```bash
# Check logs
gh run view <run-id> --log

# Re-run failed jobs
gh run rerun <run-id> --failed

# Debug locally
docker build -t sparql-agent:debug --target development .
docker run -it sparql-agent:debug /bin/bash
```

### Test Failures
```bash
# Run specific test
uv run pytest tests/test_specific.py::test_function -v

# Debug mode
uv run pytest tests/ --pdb

# See output
uv run pytest tests/ -s
```

### Deployment Issues
```bash
# Check deployment logs
./scripts/deploy.sh aws --environment prod --version v1.0.0 2>&1 | tee deploy.log

# Manual health check
curl -f https://api.example.com/health

# Check rollback
./scripts/rollback.sh --environment prod --provider aws
```

## Security Best Practices

1. **Never commit secrets** - Use GitHub Secrets
2. **Rotate credentials** - Regularly update secrets
3. **Review dependencies** - Check Dependabot PRs
4. **Monitor security alerts** - Check Security tab
5. **Update base images** - Keep Docker images current

## Performance Tips

1. **Use caching** - UV cache, Docker cache
2. **Parallel execution** - pytest-xdist
3. **Matrix optimization** - Reduce unnecessary combinations
4. **Conditional jobs** - Skip unnecessary work
5. **Artifact cleanup** - Set retention periods

## Quick Links

- [Full Documentation](.github/workflows/README.md)
- [Implementation Guide](CICD_IMPLEMENTATION.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Terraform Docs](https://www.terraform.io/docs)
- [Kubernetes Docs](https://kubernetes.io/docs)
