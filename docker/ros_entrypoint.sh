#!/bin/bash
# =============================================================================
# HelMoRo ROS 2 — Entrypoint Script
# Sources ROS 2 and workspace overlays before executing the user command
# =============================================================================
set -e

# Source ROS 2 base
source /opt/ros/${ROS_DISTRO}/setup.bash

# Source workspace if built
if [ -f "${HELMORO_WS}/install/setup.bash" ]; then
    source "${HELMORO_WS}/install/setup.bash"
fi

exec "$@"
