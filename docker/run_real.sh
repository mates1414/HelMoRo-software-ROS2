#!/bin/bash
# =============================================================================
# HelMoRo — Run Real Robot Container
# Launches the full real robot stack with hardware device access
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default arguments
LAUNCH_ARGS="${@:-}"

echo "Starting HelMoRo real robot..."
echo "  Launch args: ${LAUNCH_ARGS:-<default>}"

# Detect available devices
DEVICE_FLAGS=""
for dev in /dev/ttyACM0 /dev/ttyACM1 /dev/ttyUSB0; do
    if [ -e "$dev" ]; then
        DEVICE_FLAGS="${DEVICE_FLAGS} --device=${dev}:${dev}"
        echo "  Device: ${dev}"
    fi
done

# I2C bus for IMU
if [ -e "/dev/i2c-1" ]; then
    DEVICE_FLAGS="${DEVICE_FLAGS} --device=/dev/i2c-1:/dev/i2c-1"
    echo "  Device: /dev/i2c-1 (IMU)"
fi

docker run -it --rm \
    --name helmoro_real \
    --network host \
    --ipc host \
    --privileged \
    -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
    -e RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}" \
    -v /dev/shm:/dev/shm \
    -v /dev/bus/usb:/dev/bus/usb \
    ${DEVICE_FLAGS} \
    helmoro:real \
    ros2 launch helmoro_real_bringup helmoro_launch.py ${LAUNCH_ARGS}
