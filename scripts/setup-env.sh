#!/bin/bash
# Environment setup script
# Usage: ./setup-env.sh <environment>

set -euo pipefail

ENVIRONMENT="${1:-development}"

echo "Setting up environment: $ENVIRONMENT"

# Create necessary directories
mkdir -p logs data .cache

# Set environment variables based on environment
case $ENVIRONMENT in
    production)
        export SPARQL_AGENT_LOG_LEVEL=INFO
        export SPARQL_AGENT_WORKERS=4
        export SPARQL_AGENT_DEBUG=false
        ;;
    staging)
        export SPARQL_AGENT_LOG_LEVEL=INFO
        export SPARQL_AGENT_WORKERS=2
        export SPARQL_AGENT_DEBUG=false
        ;;
    development)
        export SPARQL_AGENT_LOG_LEVEL=DEBUG
        export SPARQL_AGENT_WORKERS=1
        export SPARQL_AGENT_DEBUG=true
        ;;
esac

echo "Environment setup completed"
