# HelMoRo-software-ROS2

**HelMoRo** (Helbling Mobile Robot) is a 4-wheeled differential-drive mobile robot built by Helbling Technik AG. This repository contains the full ROS 2 (Humble) software stack for simulation (Gazebo Ignition Fortress), real hardware operation, SLAM, autonomous navigation (Nav2), and joystick teleoperation.

> Full documentation: [helbling-technik.github.io/HelMoRo](https://helbling-technik.github.io/HelMoRo/)

---

## Architecture Overview

```
                     ┌──────────────────────────────────┐
                     │      helmoro_sim_launch.py        │  (or helmoro_launch.py for real)
                     └──────────────┬───────────────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              │                     │                      │
     ┌────────▼────────┐   ┌───────▼────────┐    ┌────────▼──────────┐
     │  Gazebo + Bridge │   │ common_launch  │    │   nav2_launch     │
     │  (sim only)      │   │                │    │  (navigation)     │
     └──────────────────┘   │ ┌────────────┐ │    └───────────────────┘
                            │ │ description│ │
                            │ │ (URDF/TF)  │ │
                            │ ├────────────┤ │
                            │ │ros2_control│ │
                            │ │(diff_drive)│ │
                            │ ├────────────┤ │
                            │ │   SLAM     │ │
                            │ ├────────────┤ │
                            │ │   EKF      │ │
                            │ ├────────────┤ │
                            │ │ twist_mux  │ │
                            │ └────────────┘ │
                            └────────────────┘
```

**Velocity command flow:**
Joystick → `helmoro_joy_control/cmd_vel` → `twist_mux` ← `nav2/cmd_vel` → `/twist_mux/cmd_vel` → relay → `/diff_drive_controller/cmd_vel` → wheels

**Odometry flow:**
Wheel encoders (or sim diff_drive_controller) → `/ekf_filter_node/wheel_odom` + IMU → EKF → `/odom` TF → SLAM → `/map` TF

---

## Repository Structure

```
HelMoRo-software-ROS2/
├── LICENSE
├── README.md
├── helmoro_base/                          # Core robot packages (common, real, sim)
│   ├── helmoro_common/
│   │   ├── helmoro_common_bringup/        # Common launch files, RViz config, twist_mux config
│   │   ├── helmoro_control/               # ros2_control URDF macros & controller YAML config
│   │   ├── helmoro_description/           # Robot URDF, meshes, C++ name/enum headers
│   │   ├── helmoro_slam/                  # SLAM Toolbox wrapper (config + launch)
│   │   └── helmoro_state_estimation/      # EKF (robot_localization) config + launch
│   ├── helmoro_real/
│   │   ├── helmoro_motors/                # RoboClaw motor driver node (Python)
│   │   └── helmoro_real_bringup/          # Real robot top-level launch (sensors + stack)
│   └── helmoro_sim/
│       ├── helmoro_gazebo_tools/          # Gazebo worlds, ROS-Ignition bridge config
│       └── helmoro_sim_bringup/           # Simulation top-level launch (Gazebo + stack)
└── helmoro_operations/                    # Optional operational capabilities
    ├── helmoro_joy_control/               # Joystick teleoperation (C++ composable node)
    └── helmoro_navigation/                # Nav2 autonomous navigation wrapper
```

---

## Packages & File Reference

### `helmoro_common_bringup` — Common Bringup

| File | Purpose |
|------|---------|
| `launch/common_launch.py` | **Core launch file** — starts robot description, ros2_control node (real only), joint_state_broadcaster, diff_drive_controller, SLAM, EKF state estimation, twist_mux, RViz (optional), and cmd_vel relay |
| `launch/rviz_launch.py` | Launches RViz2 with bundled config; adds image transport republishers for camera streams (real only) |
| `config/twist_mux.yaml` | Twist mux configuration for multiplexing joystick and nav2 velocity commands |
| `rviz/rviz_config.rviz` | Default RViz display configuration |
| `helmoro_common_bringup/namespace.py` | Utility `GetNamespacedName` substitution class for namespaced launch files |

### `helmoro_control` — ros2_control Configuration

| File | Purpose |
|------|---------|
| `config/helmoro_controller.yaml` | Controller manager config (100 Hz, Ignition hardware plugin), joint_state_broadcaster, and diff_drive_controller with wheel geometry, odom, velocity/acceleration limits |
| `urdf/helmoro_control.urdf` | Xacro macro declaring `<ros2_control>` tag with 4 wheel joints (velocity command interface, position + velocity state interfaces) |

### `helmoro_description` — Robot Model

| File | Purpose |
|------|---------|
| `urdf/helmoro.urdf` | Main robot xacro — includes parameters + segments, defines all Gazebo sensor plugins (IMU, LiDAR, depth camera, RGB camera), ign_ros2_control plugin, and wheel friction |
| `urdf/helmoro_parameters.urdf` | Xacro property definitions for all 9 links and 8 joints — dimensions, masses, inertias, mesh paths, joint origins |
| `urdf/helmoro_segments.urdf` | Xacro macros (`link_1` through `link_9`) instantiating each link's visual, collision, inertial, and joint elements; camera optical frames, fork frame, base_footprint |
| `urdf/helmoro_sim.urdf` | Top-level sim URDF — includes `helmoro.urdf` + `<ros2_control>` block using `ign_ros2_control/IgnitionSystem` |
| `urdf/helmoro_real.urdf` | Top-level real URDF — includes `helmoro.urdf` + `<ros2_control>` block using `fake_components/GenericSystem` |
| `launch/helmoro_description_launch.py` | Launches `robot_state_publisher` with sim or real URDF based on `use_sim_time` |
| `launch/test_display_launch.py` | Standalone URDF viewing — robot_state_publisher + joint_state_publisher_gui + RViz |
| `include/helmoro_description/helmoro_names.hpp` | C++ constexpr string arrays for joint, actuator, and link names |
| `include/helmoro_description/enums/enums.hpp` | C++ enums: `JointEnum`, `ActuatorEnum`, `LinkEnum`, `ActuatorModeEnum` |
| `meshes/*.STL` | 3D mesh files: Cover, Chassis, Camera, LiDAR, etc. |

### `helmoro_slam` — SLAM

| File | Purpose |
|------|---------|
| `config/slam.yaml` | slam_toolbox parameters — Ceres solver, 0.05 m resolution, 0.2–12 m laser range, loop closure enabled |
| `launch/slam_launch.py` | Launches sync or async slam_toolbox node; remaps `/scan` to `/sensors/lidar/scan` |

### `helmoro_state_estimation` — EKF State Estimation

| File | Purpose |
|------|---------|
| `config/ekf_params.yaml` | EKF config — 30 Hz, 2D mode, fuses wheel odometry (linear-x velocity) + IMU (yaw rate), publishes `odom` TF |
| `launch/helmoro_state_estimation_launch.py` | Launches `ekf_node` from robot_localization with the config; adds relay converting TwistStamped → Twist for EKF cmd_vel input |

### `helmoro_motors` — Motor Driver (Real Hardware)

| File | Purpose |
|------|---------|
| `helmoro_motors/helmoro_motors_node.py` | Main ROS node — subscribes to cmd_vel, converts to per-wheel velocities via diff-drive kinematics, sends to RoboClaw, reads encoders, publishes `/joint_states` and `/motors/odom` at 10 Hz |
| `helmoro_motors/robot_handler.py` | Hardware abstraction — initializes 2 RoboClaw controllers on `/dev/ttyACM0` and `/dev/ttyACM1`, provides wheel position/velocity getters and command senders |
| `helmoro_motors/roboclaw.py` | Full Python implementation of the RoboClaw serial protocol (speed, position, PID, encoder reading) |
| `launch/helmoro_motors.launch.py` | Launches `helmoro_motors_node` |

### `helmoro_real_bringup` — Real Robot Bringup

| File | Purpose |
|------|---------|
| `launch/helmoro_launch.py` | **Main real robot launch** — starts IMU, LiDAR, camera, motors, common stack, navigation, and odom relay |
| `launch/imu_launch.py` | Launches BNO055 IMU driver (I2C) |
| `launch/lidar_launch.py` | Launches RPLiDAR A2M8 driver under `sensors/lidar` namespace |
| `launch/camera_launch.py` | Launches Orbbec Astra camera under `sensors` namespace |
| `config/bno055_params_i2c.yaml` | BNO055 config — I2C bus 1, address 0x28, 100 Hz, placement P2 |

### `helmoro_gazebo_tools` — Gazebo Simulation Tools

| File | Purpose |
|------|---------|
| `config/ros_gazebo_bridge.yaml` | Bridge topic mappings (Gazebo ↔ ROS 2): clock, scan, IMU, depth camera, RGB camera, camera_info |
| `launch/helmoro_ros_bridge_launch.py` | Launches `ros_gz_bridge` parameter_bridge node with the YAML config |
| `worlds/depot.sdf` | Gazebo SDF world — warehouse/depot environment |
| `worlds/empty.sdf` | Gazebo SDF world — empty environment |

### `helmoro_sim_bringup` — Simulation Bringup

| File | Purpose |
|------|---------|
| `launch/helmoro_sim_launch.py` | **Main sim launch** — starts Gazebo, spawns robot, loads controllers (joint_state_broadcaster → diff_drive_controller), relays odom to EKF, optionally launches joystick control |
| `launch/gazebo_launch.py` | Launches Gazebo Ignition with the selected world, sets resource paths, starts ROS bridge |
| `launch/helmoro_spawn_launch.py` | Spawns HelMoRo into Gazebo at configurable pose, launches common stack (`common_launch.py` with `use_sim_time=true`) and navigation |

### `helmoro_joy_control` — Joystick Teleoperation

| File | Purpose |
|------|---------|
| `src/helmoro_joy_control.cpp` | C++ composable node — maps left/right triggers to forward/backward velocity, left stick to angular velocity; applies scaling and max limits; publishes `cmd_vel` |
| `include/helmoro_joy_control/helmoro_joy_control.hpp` | C++ header — `HelmoroJoyControl` node class declaration |
| `param/parameters.yaml` | Scaling factors (1.0), max linear vel (1.1 m/s), max angular vel (10.5 rad/s) |
| `launch/joy_control_launch.py` | Launches `joy_node` (deadzone 0.2, 20 Hz) and `helmoro_joy_control` node under `helmoro_joy_control` namespace |

### `helmoro_navigation` — Autonomous Navigation

| File | Purpose |
|------|---------|
| `config/nav2.yaml` | Full Nav2 config — BT navigator, MPPI controller (max 0.5 m/s), local costmap (5×5 m), global costmap, NavFn planner, smoother, behaviors (spin, backup, wait), velocity smoother, waypoint follower |
| `launch/nav2_launch.py` | Launches Nav2 via `nav2_bringup/navigation_launch.py` with custom params; remaps costmap scan topics to `/sensors/lidar/scan` |

---

## Installation

```bash
# Create workspace
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/mates1414/HelMoRo-software-ROS2.git

# Install dependencies
cd ~/ros2_ws
sudo apt-get update
rosdep install --from-path src -yi

# Build
source /opt/ros/humble/setup.bash
colcon build --symlink-install

# Source workspace
source ~/ros2_ws/install/setup.bash
```

> **Tip:** Add `source /opt/ros/humble/setup.bash` and `source ~/ros2_ws/install/setup.bash` to your `~/.bashrc` to auto-source on every new terminal.

---

## Usage

### Simulation

```bash
# Start Gazebo simulation with robot + full stack (SLAM, EKF, Nav2)
ros2 launch helmoro_sim_bringup helmoro_sim_launch.py

# With joystick control enabled
ros2 launch helmoro_sim_bringup helmoro_sim_launch.py use_joy:=true

# Choose a different world
ros2 launch helmoro_sim_bringup helmoro_sim_launch.py world:=empty

# Use 4-wheel drive mode (independent per-wheel control, wheels_per_side=2)
ros2 launch helmoro_sim_bringup helmoro_sim_launch.py drive_mode:=4wd
```

### Real Robot

```bash
# Launch full real robot stack (sensors, motors, SLAM, EKF, Nav2)
ros2 launch helmoro_real_bringup helmoro_launch.py

# Launch with 4WD mode (requires 4 independent motors + encoders)
ros2 launch helmoro_real_bringup helmoro_launch.py drive_mode:=4wd
```

### Control (separate terminal)

```bash
# Joystick teleoperation
ros2 launch helmoro_joy_control joy_control_launch.py

# Autonomous navigation (if not already included in bringup)
ros2 launch helmoro_navigation nav2_launch.py use_sim_time:=true
```

### Verify Controllers

```bash
# Check controller status
ros2 control list_controllers

# Manually activate if needed
ros2 run controller_manager spawner joint_state_broadcaster
ros2 run controller_manager spawner diff_drive_controller

ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active diff_drive_controller
```

---

## License

BSD — see [LICENSE](LICENSE) for details.
