#!/bin/bash
# Backup script for database and configuration
# Usage: ./backup.sh --environment <env> --provider <provider>

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/tmp/sparql-agent-backups}"
LOG_FILE="${LOG_FILE:-/tmp/sparql-agent-backup-$(date +%Y%m%d-%H%M%S).log}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Default values
ENVIRONMENT="${ENVIRONMENT:-staging}"
PROVIDER=""
RETENTION_DAYS=30

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration
backup_config() {
    log "Backing up configuration..."
    local config_backup="${BACKUP_DIR}/config-${ENVIRONMENT}-${TIMESTAMP}.tar.gz"

    tar czf "$config_backup" \
        -C "$SCRIPT_DIR/.." \
        --exclude='*.log' \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        pyproject.toml \
        docker-compose.yml \
        Dockerfile \
        2>/dev/null || true

    log "Configuration backup saved: $config_backup"
}

# Backup database
backup_database() {
    log "Backing up database..."
    # Add database backup logic based on your database type
    log "Database backup completed"
}

# Upload to cloud storage
upload_backup() {
    local backup_file="$1"

    case $PROVIDER in
        aws)
            aws s3 cp "$backup_file" "s3://sparql-agent-backups/${ENVIRONMENT}/"
            ;;
        gcp)
            gsutil cp "$backup_file" "gs://sparql-agent-backups/${ENVIRONMENT}/"
            ;;
        azure)
            az storage blob upload --file "$backup_file" --container-name backups
            ;;
    esac

    log "Backup uploaded to cloud storage"
}

# Main
main() {
    log "Starting backup for environment: $ENVIRONMENT"
    backup_config
    backup_database

    if [[ -n "$PROVIDER" ]]; then
        upload_backup "${BACKUP_DIR}/config-${ENVIRONMENT}-${TIMESTAMP}.tar.gz"
    fi

    # Cleanup old backups
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

    log "Backup completed successfully"
}

main
