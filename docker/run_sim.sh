#!/bin/bash
# =============================================================================
# HelMoRo — Run Simulation Container
# Launches Gazebo simulation with X11 forwarding and optional NVIDIA GPU
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Allow X11 connections from container
xhost +local:docker 2>/dev/null || true

# Check for NVIDIA GPU
GPU_FLAGS=""
if command -v nvidia-smi &>/dev/null; then
    echo "NVIDIA GPU detected — enabling GPU acceleration"
    GPU_FLAGS="--gpus all"
fi

# Default arguments
LAUNCH_ARGS="${@:-}"

echo "Starting HelMoRo simulation..."
echo "  Launch args: ${LAUNCH_ARGS:-<default>}"

docker run -it --rm \
    --name helmoro_sim \
    --network host \
    --ipc host \
    ${GPU_FLAGS} \
    -e DISPLAY="${DISPLAY}" \
    -e QT_X11_NO_MITSHM=1 \
    -e XAUTHORITY=/tmp/.Xauthority \
    -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
    -e RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}" \
    -e NVIDIA_VISIBLE_DEVICES="${NVIDIA_VISIBLE_DEVICES:-all}" \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    -v "${XAUTHORITY:-$HOME/.Xauthority}":/tmp/.Xauthority:ro \
    -v /dev/shm:/dev/shm \
    helmoro:sim \
    ros2 launch helmoro_sim_bringup helmoro_sim_launch.py ${LAUNCH_ARGS}

# Revoke X11 permissions
xhost -local:docker 2>/dev/null || true
