# HelMoRo Docker Setup

Docker images for the HelMoRo ROS 2 stack, eliminating dependency issues across machines.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  helmoro:base                        │
│  ros:humble-ros-base-jammy                          │
│  + ros2_control, SLAM, Nav2, EKF, twist_mux, RViz  │
│  + workspace source code                            │
└───────────────┬─────────────────┬───────────────────┘
                │                 │
    ┌───────────▼──────┐  ┌──────▼────────────┐
    │   helmoro:sim    │  │   helmoro:real     │
    │ + Gazebo Fortress│  │ + BNO055 driver    │
    │ + ign_ros2_ctrl  │  │ + RPLiDAR driver   │
    │ + GL/X11 libs    │  │ + Orbbec camera    │
    │ - real packages  │  │ + pyserial/i2c     │
    └──────────────────┘  │ - sim packages     │
                          └───────────────────┘
```

## Prerequisites

- Docker Engine ≥ 20.10
- Docker Compose v2
- (Simulation) NVIDIA GPU + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for GPU-accelerated Gazebo
- (Real robot) USB device access permissions

## Quick Start

### Build Images

```bash
# Build all images (base → sim + real)
./docker/build.sh all

# Build only simulation
./docker/build.sh sim

# Build only real robot
./docker/build.sh real

# Rebuild without cache
./docker/build.sh all --no-cache
```

### Run Simulation (Development PC)

```bash
# Option 1: Direct script
./docker/run_sim.sh

# With custom launch arguments
./docker/run_sim.sh use_joy:=true world:=empty

# Option 2: Docker Compose
cd docker
docker compose -f docker-compose.sim.yaml up helmoro-sim

# With joystick teleoperation
docker compose -f docker-compose.sim.yaml --profile joy up
```

### Run Real Robot (Onboard Computer)

```bash
# Option 1: Direct script
./docker/run_real.sh

# Option 2: Docker Compose
cd docker
docker compose -f docker-compose.real.yaml up helmoro-real
```

### Interactive Shell

```bash
# Open a shell in the sim container (new or running)
./docker/shell.sh sim

# Open a shell in the real container
./docker/shell.sh real
```

## Docker Compose Services

### Simulation (`docker-compose.sim.yaml`)

| Service | Description |
|---------|-------------|
| `helmoro-sim` | Full simulation (Gazebo + RViz + Nav2 + SLAM) |
| `helmoro-joy` | Joystick teleoperation (activate with `--profile joy`) |

### Real Robot (`docker-compose.real.yaml`)

| Service | Description |
|---------|-------------|
| `helmoro-real` | Full real robot stack (sensors + motors + Nav2 + SLAM) |
| `helmoro-rviz` | Remote RViz visualization (activate with `--profile rviz`) |

## Development Workflow

### Live Code Editing

Uncomment the source volume mount in the compose file to edit code on the host and see changes reflected inside the container:

```yaml
volumes:
  - ..:/ros2_ws/src/HelMoRo-software-ROS2:rw
```

Then rebuild inside the container:

```bash
./docker/shell.sh sim
# Inside container:
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### Multi-Machine ROS 2 Communication

Containers use `network_mode: host` so ROS 2 DDS discovery works across machines on the same network. Set the same `ROS_DOMAIN_ID` on all machines:

```bash
export ROS_DOMAIN_ID=42
./docker/run_sim.sh    # on PC A
./docker/run_real.sh   # on Robot
```

### GPU Acceleration

The simulation compose file automatically requests NVIDIA GPU access. If you don't have an NVIDIA GPU, set:

```bash
export LIBGL_ALWAYS_SOFTWARE=1
```

For Intel/AMD GPUs, add this volume to the compose file:

```yaml
volumes:
  - /dev/dri:/dev/dri
```

## Troubleshooting

### Display not working (GUI)

```bash
# Allow Docker to access your X display
xhost +local:docker

# Verify DISPLAY is set
echo $DISPLAY
```

### USB devices not detected (real robot)

```bash
# Check devices exist on host
ls -la /dev/ttyACM* /dev/ttyUSB* /dev/i2c-*

# Add user to dialout group (for serial access without privileged mode)
sudo usermod -aG dialout $USER

# Create udev rules for persistent device names (recommended)
# /etc/udev/rules.d/99-helmoro.rules:
SUBSYSTEM=="tty", ATTRS{idVendor}=="03eb", ATTRS{idProduct}=="2404", SYMLINK+="roboclaw0"
```

### Gazebo crashes or black screen

```bash
# Test OpenGL inside container
./docker/shell.sh sim
glxinfo | grep "OpenGL renderer"

# Fall back to software rendering
export LIBGL_ALWAYS_SOFTWARE=1
./docker/run_sim.sh
```

### Rebuilding after source changes

```bash
# If using volume mount — just rebuild inside container
docker exec -it helmoro_sim bash -c "cd /ros2_ws && colcon build --symlink-install"

# If image-baked — rebuild the image
./docker/build.sh sim
```

## File Reference

```
docker/
├── Dockerfile.base            # Base image: ROS 2 Humble + common deps
├── Dockerfile.sim             # Simulation: + Gazebo Fortress + GUI
├── Dockerfile.real            # Real robot: + hardware drivers
├── docker-compose.sim.yaml    # Compose for simulation PC
├── docker-compose.real.yaml   # Compose for robot onboard PC
├── ros_entrypoint.sh          # Container entrypoint (sources ROS)
├── build.sh                   # Build helper script
├── run_sim.sh                 # Run simulation shortcut
├── run_real.sh                # Run real robot shortcut
├── shell.sh                   # Interactive shell access
└── README.md                  # This file
```
