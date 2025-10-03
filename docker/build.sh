#!/bin/bash
# Docker build script for SPARQL Agent
# Supports multi-platform builds, caching, and tagging strategies

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="sparql-agent"
REGISTRY="${DOCKER_REGISTRY:-}"
VERSION="${VERSION:-$(git describe --tags --always --dirty 2>/dev/null || echo 'dev')}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')

# Build settings
PLATFORM="${PLATFORM:-linux/amd64,linux/arm64}"
CACHE_FROM="${CACHE_FROM:-}"
PUSH="${PUSH:-false}"
TARGET="${TARGET:-runtime}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

print_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Build Docker images for SPARQL Agent with advanced options.

OPTIONS:
    -t, --target TARGET       Build target (runtime, development, testing, mcp-server)
                              Default: runtime
    -v, --version VERSION     Version tag (default: git tag or 'dev')
    -r, --registry REGISTRY   Docker registry URL
    -p, --platform PLATFORM   Target platforms (default: linux/amd64,linux/arm64)
    --push                    Push images to registry
    --no-cache                Build without cache
    --cache-from IMAGE        Use image as cache source
    -h, --help                Show this help message

EXAMPLES:
    # Build production image
    $0 -t runtime -v 1.0.0

    # Build development image
    $0 -t development

    # Build and push multi-arch
    $0 -t runtime --platform linux/amd64,linux/arm64 --push -r myregistry.com

    # Build MCP server
    $0 -t mcp-server

    # Build with cache
    $0 --cache-from myregistry.com/sparql-agent:latest

EOF
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--target)
                TARGET="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -p|--platform)
                PLATFORM="$2"
                shift 2
                ;;
            --push)
                PUSH="true"
                shift
                ;;
            --no-cache)
                NO_CACHE="--no-cache"
                shift
                ;;
            --cache-from)
                CACHE_FROM="$2"
                shift 2
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# Validate requirements
check_requirements() {
    log_section "Checking Requirements"

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    log_info "Docker version: $(docker --version)"

    # Check for buildx
    if ! docker buildx version &> /dev/null; then
        log_warn "Docker Buildx not available - multi-platform builds disabled"
        PLATFORM="linux/amd64"
    else
        log_info "Docker Buildx version: $(docker buildx version)"
    fi
}

# Setup buildx builder
setup_buildx() {
    if docker buildx version &> /dev/null; then
        log_section "Setting up Docker Buildx"

        # Create builder if it doesn't exist
        if ! docker buildx inspect sparql-agent-builder &> /dev/null; then
            log_info "Creating buildx builder: sparql-agent-builder"
            docker buildx create --name sparql-agent-builder --use
        else
            log_info "Using existing builder: sparql-agent-builder"
            docker buildx use sparql-agent-builder
        fi

        # Bootstrap builder
        docker buildx inspect --bootstrap
    fi
}

# Generate image tags
generate_tags() {
    local target_suffix=""
    case "$TARGET" in
        development)
            target_suffix="-dev"
            ;;
        testing)
            target_suffix="-test"
            ;;
        mcp-server)
            target_suffix="-mcp"
            ;;
    esac

    if [ -n "$REGISTRY" ]; then
        BASE_TAG="${REGISTRY}/${PROJECT_NAME}"
    else
        BASE_TAG="${PROJECT_NAME}"
    fi

    TAGS=(
        "${BASE_TAG}:${VERSION}${target_suffix}"
        "${BASE_TAG}:latest${target_suffix}"
    )

    # Add semantic version tags if version is semver
    if [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f1,2)
        TAGS+=(
            "${BASE_TAG}:${MAJOR}${target_suffix}"
            "${BASE_TAG}:${MINOR}${target_suffix}"
        )
    fi
}

# Build image
build_image() {
    log_section "Building Docker Image"

    log_info "Project: ${PROJECT_NAME}"
    log_info "Target: ${TARGET}"
    log_info "Version: ${VERSION}"
    log_info "Build Date: ${BUILD_DATE}"
    log_info "VCS Ref: ${VCS_REF}"
    log_info "Platform: ${PLATFORM}"

    # Generate tags
    generate_tags

    log_info "Tags:"
    for tag in "${TAGS[@]}"; do
        log_info "  - ${tag}"
    done

    # Build tag arguments
    TAG_ARGS=""
    for tag in "${TAGS[@]}"; do
        TAG_ARGS="${TAG_ARGS} -t ${tag}"
    done

    # Build cache arguments
    CACHE_ARGS=""
    if [ -n "$CACHE_FROM" ]; then
        CACHE_ARGS="--cache-from ${CACHE_FROM}"
        log_info "Cache from: ${CACHE_FROM}"
    fi

    # Build command
    BUILD_CMD="docker buildx build"
    BUILD_CMD="${BUILD_CMD} --target ${TARGET}"
    BUILD_CMD="${BUILD_CMD} --platform ${PLATFORM}"
    BUILD_CMD="${BUILD_CMD} ${TAG_ARGS}"
    BUILD_CMD="${BUILD_CMD} --build-arg VERSION=${VERSION}"
    BUILD_CMD="${BUILD_CMD} --build-arg BUILD_DATE=${BUILD_DATE}"
    BUILD_CMD="${BUILD_CMD} --build-arg VCS_REF=${VCS_REF}"
    BUILD_CMD="${BUILD_CMD} ${CACHE_ARGS}"
    BUILD_CMD="${BUILD_CMD} ${NO_CACHE:-}"

    if [ "$PUSH" = "true" ]; then
        BUILD_CMD="${BUILD_CMD} --push"
        log_info "Push: enabled"
    else
        BUILD_CMD="${BUILD_CMD} --load"
        log_info "Push: disabled (loading to local Docker)"
    fi

    BUILD_CMD="${BUILD_CMD} ."

    log_info "Build command:"
    echo "$BUILD_CMD"
    echo

    # Execute build
    log_info "Starting build..."
    if eval "$BUILD_CMD"; then
        log_section "Build Successful"
        log_info "Image built successfully: ${TAGS[0]}"

        # Show image size (for local builds)
        if [ "$PUSH" != "true" ]; then
            log_info "Image size:"
            docker images "${TAGS[0]}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
        fi

        return 0
    else
        log_error "Build failed"
        return 1
    fi
}

# Scan image for vulnerabilities (if trivy is available)
scan_image() {
    if command -v trivy &> /dev/null && [ "$PUSH" != "true" ]; then
        log_section "Scanning Image for Vulnerabilities"

        log_info "Running Trivy scan on ${TAGS[0]}..."
        trivy image --severity HIGH,CRITICAL "${TAGS[0]}" || log_warn "Vulnerabilities found"
    fi
}

# Show build summary
show_summary() {
    log_section "Build Summary"

    echo -e "${GREEN}✓${NC} Build completed successfully"
    echo -e "\n${BLUE}Image Information:${NC}"
    echo -e "  Project: ${PROJECT_NAME}"
    echo -e "  Target: ${TARGET}"
    echo -e "  Version: ${VERSION}"
    echo -e "  Platforms: ${PLATFORM}"
    echo -e "\n${BLUE}Tags:${NC}"
    for tag in "${TAGS[@]}"; do
        echo -e "  • ${tag}"
    done

    if [ "$PUSH" = "true" ]; then
        echo -e "\n${GREEN}✓${NC} Images pushed to registry"
    else
        echo -e "\n${YELLOW}ℹ${NC} Images loaded to local Docker"
        echo -e "\n${BLUE}Next steps:${NC}"
        echo -e "  • Test: docker run --rm ${TAGS[0]}"
        echo -e "  • Push: docker push ${TAGS[0]}"
        echo -e "  • Scan: trivy image ${TAGS[0]}"
    fi
}

# Main execution
main() {
    parse_args "$@"
    check_requirements
    setup_buildx
    build_image
    scan_image
    show_summary
}

# Run main
main "$@"
