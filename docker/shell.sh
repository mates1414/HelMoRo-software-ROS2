#!/bin/bash
# =============================================================================
# HelMoRo — Open an interactive shell in a running or new container
# Usage: ./shell.sh [sim|real]
# =============================================================================
set -e

TARGET="${1:-sim}"

case "$TARGET" in
    sim)
        IMAGE="helmoro:sim"
        CONTAINER="helmoro_sim"
        ;;
    real)
        IMAGE="helmoro:real"
        CONTAINER="helmoro_real"
        ;;
    *)
        echo "Usage: $0 [sim|real]"
        exit 1
        ;;
esac

# If container is already running, exec into it
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "Attaching to running container: ${CONTAINER}"
    docker exec -it "${CONTAINER}" bash
else
    echo "Starting new ${TARGET} shell..."
    
    EXTRA_FLAGS=""
    if [ "$TARGET" = "sim" ]; then
        xhost +local:docker 2>/dev/null || true
        GPU_FLAGS=""
        if command -v nvidia-smi &>/dev/null; then
            GPU_FLAGS="--gpus all"
        fi
        EXTRA_FLAGS="${GPU_FLAGS} \
            -e DISPLAY=${DISPLAY} \
            -e QT_X11_NO_MITSHM=1 \
            -e XAUTHORITY=/tmp/.Xauthority \
            -e NVIDIA_VISIBLE_DEVICES=${NVIDIA_VISIBLE_DEVICES:-all} \
            -e NVIDIA_DRIVER_CAPABILITIES=all \
            -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
            -v ${XAUTHORITY:-$HOME/.Xauthority}:/tmp/.Xauthority:ro"
    fi
    
    docker run -it --rm \
        --name "${CONTAINER}_shell" \
        --network host \
        --ipc host \
        -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
        -e RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}" \
        -v /dev/shm:/dev/shm \
        ${EXTRA_FLAGS} \
        "${IMAGE}" \
        bash
fi
