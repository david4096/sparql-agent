#!/bin/bash
# Verify deployment status and integrity
# Usage: ./verify-deployment.sh --environment <env> --version <version>

set -euo pipefail

ENVIRONMENT="${ENVIRONMENT:-staging}"
VERSION="${VERSION:-latest}"

echo "Verifying deployment: $ENVIRONMENT ($VERSION)"

# Check service health
echo "Checking service health..."
curl -sf "http://localhost:8000/health" || exit 1

# Check version
echo "Checking deployed version..."
DEPLOYED_VERSION=$(curl -s "http://localhost:8000/version" | jq -r '.version')

if [[ "$DEPLOYED_VERSION" == "$VERSION" ]]; then
    echo "Version verified: $DEPLOYED_VERSION"
else
    echo "ERROR: Version mismatch (expected: $VERSION, got: $DEPLOYED_VERSION)"
    exit 1
fi

echo "Deployment verification successful"
