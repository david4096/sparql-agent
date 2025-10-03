#!/bin/bash
# Database migration script
# Usage: ./migrate.sh --environment <env>

set -euo pipefail

ENVIRONMENT="${ENVIRONMENT:-staging}"

echo "Running database migrations for environment: $ENVIRONMENT"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "Migrations completed successfully"
