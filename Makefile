# Makefile for SPARQL Agent Docker operations
# Provides convenient shortcuts for common Docker tasks

.PHONY: help build run stop logs shell test clean dev-up dev-down k8s-deploy k8s-delete

# Default target
.DEFAULT_GOAL := help

# Variables
IMAGE_NAME ?= sparql-agent
VERSION ?= latest
REGISTRY ?=
COMPOSE_FILE ?= docker-compose.yml
DEV_COMPOSE_FILE ?= docker-compose.dev.yml

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo "$(GREEN)SPARQL Agent Docker Management$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(YELLOW)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Build

build: ## Build production Docker image
	@echo "$(GREEN)Building production image...$(NC)"
	./docker/build.sh -t runtime -v $(VERSION)

build-dev: ## Build development Docker image
	@echo "$(GREEN)Building development image...$(NC)"
	./docker/build.sh -t development

build-mcp: ## Build MCP server Docker image
	@echo "$(GREEN)Building MCP server image...$(NC)"
	./docker/build.sh -t mcp-server

build-all: build build-dev build-mcp ## Build all Docker images
	@echo "$(GREEN)All images built successfully!$(NC)"

build-multiarch: ## Build multi-architecture images
	@echo "$(GREEN)Building multi-architecture images...$(NC)"
	./docker/build.sh -t runtime --platform linux/amd64,linux/arm64

push: ## Push images to registry
	@echo "$(GREEN)Pushing images to registry...$(NC)"
	./docker/build.sh -t runtime --push -r $(REGISTRY)

##@ Run

run: ## Run production container
	@echo "$(GREEN)Starting production container...$(NC)"
	./docker/run.sh --mode web --port 8000

run-mcp: ## Run MCP server container
	@echo "$(GREEN)Starting MCP server...$(NC)"
	./docker/run.sh --mode mcp --port 3000

run-cli: ## Run interactive CLI
	@echo "$(GREEN)Starting interactive CLI...$(NC)"
	./docker/run.sh --mode cli --fg

stop: ## Stop running containers
	@echo "$(YELLOW)Stopping containers...$(NC)"
	docker stop sparql-agent sparql-agent-mcp 2>/dev/null || true

restart: stop run ## Restart containers
	@echo "$(GREEN)Containers restarted$(NC)"

##@ Docker Compose

up: ## Start all services with docker-compose
	@echo "$(GREEN)Starting all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down

logs: ## View logs from all services
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api: ## View API server logs
	docker-compose -f $(COMPOSE_FILE) logs -f sparql-agent-api

logs-mcp: ## View MCP server logs
	docker-compose -f $(COMPOSE_FILE) logs -f sparql-agent-mcp

ps: ## Show running services
	docker-compose -f $(COMPOSE_FILE) ps

restart-compose: down up ## Restart docker-compose stack
	@echo "$(GREEN)Services restarted$(NC)"

##@ Development

dev-up: ## Start development environment
	@echo "$(GREEN)Starting development environment...$(NC)"
	./docker/dev.sh up

dev-down: ## Stop development environment
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	./docker/dev.sh down

dev-logs: ## View development logs
	./docker/dev.sh logs -f

dev-shell: ## Open shell in development container
	@echo "$(GREEN)Opening development shell...$(NC)"
	./docker/dev.sh shell

dev-test: ## Run tests in development
	@echo "$(GREEN)Running tests...$(NC)"
	./docker/dev.sh test

dev-rebuild: ## Rebuild development containers
	@echo "$(GREEN)Rebuilding development containers...$(NC)"
	docker-compose -f $(DEV_COMPOSE_FILE) build --no-cache

dev-clean: ## Clean development environment
	@echo "$(RED)Cleaning development environment...$(NC)"
	./docker/dev.sh clean

##@ Testing

test: ## Run tests in container
	@echo "$(GREEN)Running tests...$(NC)"
	docker run --rm -v $(PWD)/htmlcov:/app/htmlcov $(IMAGE_NAME):test

test-coverage: test ## Run tests with coverage report
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"
	@[ -f htmlcov/index.html ] && open htmlcov/index.html || echo "Coverage report not found"

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	docker run --rm $(IMAGE_NAME):test pytest tests/integration/

##@ Utilities

shell: ## Open shell in running container
	@echo "$(GREEN)Opening shell...$(NC)"
	docker exec -it sparql-agent /bin/sh

shell-root: ## Open root shell in running container
	@echo "$(GREEN)Opening root shell...$(NC)"
	docker exec -it -u root sparql-agent /bin/sh

health: ## Check container health
	@echo "$(GREEN)Checking container health...$(NC)"
	@curl -f http://localhost:8000/health && echo "\n$(GREEN)✓ API is healthy$(NC)" || echo "\n$(RED)✗ API is unhealthy$(NC)"

inspect: ## Inspect container
	docker inspect sparql-agent

stats: ## Show container stats
	docker stats sparql-agent

##@ Cleanup

clean: ## Remove stopped containers and dangling images
	@echo "$(YELLOW)Cleaning up...$(NC)"
	docker container prune -f
	docker image prune -f

clean-all: ## Remove all containers, images, and volumes
	@echo "$(RED)WARNING: This will remove ALL SPARQL Agent containers, images, and volumes!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		docker-compose -f $(DEV_COMPOSE_FILE) down -v; \
		docker rmi -f $$(docker images -q $(IMAGE_NAME)) 2>/dev/null || true; \
		docker volume prune -f; \
		echo "$(GREEN)Cleanup complete$(NC)"; \
	fi

clean-volumes: ## Remove all volumes
	@echo "$(YELLOW)Removing volumes...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v
	docker volume prune -f

##@ Security

scan: ## Scan image for vulnerabilities
	@echo "$(GREEN)Scanning image for vulnerabilities...$(NC)"
	trivy image $(IMAGE_NAME):$(VERSION)

scan-critical: ## Scan for critical vulnerabilities only
	@echo "$(GREEN)Scanning for critical vulnerabilities...$(NC)"
	trivy image --severity CRITICAL,HIGH $(IMAGE_NAME):$(VERSION)

sign: ## Sign image with cosign
	@echo "$(GREEN)Signing image...$(NC)"
	cosign sign --key cosign.key $(IMAGE_NAME):$(VERSION)

verify: ## Verify image signature
	@echo "$(GREEN)Verifying image signature...$(NC)"
	cosign verify --key cosign.pub $(IMAGE_NAME):$(VERSION)

##@ Kubernetes

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(GREEN)Deploying to Kubernetes...$(NC)"
	kubectl apply -f k8s/

k8s-delete: ## Delete from Kubernetes
	@echo "$(RED)Deleting from Kubernetes...$(NC)"
	kubectl delete -f k8s/

k8s-status: ## Check Kubernetes deployment status
	@echo "$(GREEN)Kubernetes Status:$(NC)"
	kubectl get all -n sparql-agent

k8s-logs: ## View Kubernetes logs
	kubectl logs -f deployment/sparql-agent-api -n sparql-agent

k8s-shell: ## Open shell in Kubernetes pod
	@echo "$(GREEN)Opening shell in Kubernetes pod...$(NC)"
	kubectl exec -it deployment/sparql-agent-api -n sparql-agent -- /bin/sh

k8s-port-forward: ## Port forward Kubernetes service
	@echo "$(GREEN)Port forwarding to localhost:8000...$(NC)"
	kubectl port-forward -n sparql-agent svc/sparql-agent-api-service 8000:8000

k8s-scale: ## Scale Kubernetes deployment
	@read -p "Number of replicas: " replicas; \
	kubectl scale deployment/sparql-agent-api -n sparql-agent --replicas=$$replicas

##@ CI/CD

ci-build: ## Build for CI/CD
	@echo "$(GREEN)Building for CI/CD...$(NC)"
	docker build --target runtime -t $(IMAGE_NAME):$(VERSION) .

ci-test: ## Run CI/CD tests
	@echo "$(GREEN)Running CI/CD tests...$(NC)"
	docker build --target testing -t $(IMAGE_NAME):test .
	docker run --rm $(IMAGE_NAME):test

ci-push: ## Push to registry (CI/CD)
	@echo "$(GREEN)Pushing to registry...$(NC)"
	docker tag $(IMAGE_NAME):$(VERSION) $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)

##@ Documentation

docs: ## Open documentation
	@echo "$(GREEN)Opening documentation...$(NC)"
	@[ -f DOCKER.md ] && open DOCKER.md || echo "DOCKER.md not found"

readme: ## Open README
	@echo "$(GREEN)Opening README...$(NC)"
	@[ -f README.md ] && open README.md || echo "README.md not found"

##@ Quick Actions

quick-start: build run ## Quick start: build and run
	@echo "$(GREEN)Quick start complete!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

demo: ## Run demo environment
	@echo "$(GREEN)Starting demo environment...$(NC)"
	@echo "1. Building images..."
	@make build-dev
	@echo "2. Starting services..."
	@make dev-up
	@echo "$(GREEN)Demo environment ready!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Redis Commander: http://localhost:8081"

full-deploy: build-all up ## Full deployment: build all and start
	@echo "$(GREEN)Full deployment complete!$(NC)"

# Version information
version: ## Show version information
	@echo "Image: $(IMAGE_NAME):$(VERSION)"
	@echo "Registry: $(REGISTRY)"
	@docker images $(IMAGE_NAME) --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
