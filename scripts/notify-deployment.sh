#!/bin/bash
# Send deployment notifications
# Usage: ./notify-deployment.sh --provider <provider> --environment <env> --version <version> --status <status>

set -euo pipefail

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --provider) PROVIDER="$2"; shift 2 ;;
        --environment) ENVIRONMENT="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --status) STATUS="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Prepare notification message
MESSAGE="Deployment Status: $STATUS
Environment: $ENVIRONMENT
Provider: $PROVIDER
Version: $VERSION
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "$MESSAGE"

# Send to Slack (if webhook configured)
if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"$MESSAGE\"}"
fi

# Send email (if configured)
if [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
    echo "$MESSAGE" | mail -s "SPARQL Agent Deployment: $STATUS" "$NOTIFICATION_EMAIL"
fi
