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

# For interactive bash shells, also write to .bashrc so every
# 'docker exec ... bash' session is pre-sourced automatically
if [ ! -f /root/.bashrc_ros_sourced ]; then
    echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc
    echo "[ -f ${HELMORO_WS}/install/setup.bash ] && source ${HELMORO_WS}/install/setup.bash" >> /root/.bashrc
    touch /root/.bashrc_ros_sourced
fi

exec "$@"
