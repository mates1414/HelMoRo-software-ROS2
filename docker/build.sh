#!/bin/bash
# =============================================================================
# HelMoRo — Docker Build Script
# Builds the base, simulation, and/or real robot Docker images
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "Usage: $0 [base|sim|real|jetson|all] [--no-cache]"
    echo ""
    echo "Targets:"
    echo "  base       Build the base image only"
    echo "  sim        Build the simulation image (includes base)"
    echo "  real       Build the real robot image (includes base) — original RoboClaw hardware"
    echo "  jetson     Build the Jetson Orin Nano image — BTS7960B/Pico/IMX219/A1M8 hardware"
    echo "  all        Build base + sim + real (default)"
    echo ""
    echo "Options:"
    echo "  --no-cache Build without Docker cache"
    exit 1
}

TARGET="${1:-all}"
CACHE_FLAG=""

if [[ "$2" == "--no-cache" ]] || [[ "$1" == "--no-cache" ]]; then
    CACHE_FLAG="--no-cache"
    if [[ "$1" == "--no-cache" ]]; then
        TARGET="all"
    fi
fi

build_base() {
    echo -e "${YELLOW}Building base image...${NC}"
    docker build \
        ${CACHE_FLAG} \
        -f "${SCRIPT_DIR}/Dockerfile.base" \
        -t helmoro:base \
        "${PROJECT_DIR}"
    echo -e "${GREEN}✓ helmoro:base built successfully${NC}"
}

build_sim() {
    echo -e "${YELLOW}Building simulation image...${NC}"
    docker build \
        ${CACHE_FLAG} \
        -f "${SCRIPT_DIR}/Dockerfile.sim" \
        -t helmoro:sim \
        "${PROJECT_DIR}"
    echo -e "${GREEN}✓ helmoro:sim built successfully${NC}"
}

build_real() {
    echo -e "${YELLOW}Building real robot image...${NC}"
    docker build \
        ${CACHE_FLAG} \
        -f "${SCRIPT_DIR}/Dockerfile.real" \
        -t helmoro:real \
        "${PROJECT_DIR}"
    echo -e "${GREEN}✓ helmoro:real built successfully${NC}"
}

build_jetson() {
    echo -e "${YELLOW}Building Jetson Orin Nano image...${NC}"
    docker build \
        ${CACHE_FLAG} \
        -f "${SCRIPT_DIR}/Dockerfile.jetson" \
        -t helmoro:jetson \
        "${PROJECT_DIR}"
    echo -e "${GREEN}✓ helmoro:jetson built successfully${NC}"
}

cd "${PROJECT_DIR}"

case "$TARGET" in
    base)
        build_base
        ;;
    sim)
        build_base
        build_sim
        ;;
    real)
        build_base
        build_real
        ;;
    jetson)
        build_jetson
        ;;
    all)
        build_base
        build_sim
        build_real
        ;;
    *)
        usage
        ;;
esac

echo ""
echo -e "${GREEN}Build complete!${NC}"
echo "Available images:"
docker images --filter=reference='helmoro:*' --format "  {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"
