# HelMoRo — Real Robot Setup & Run Guide

Complete guide to get the robot running with the updated hardware:

| Component | Hardware | Interface |
|-----------|----------|-----------|
| Compute | NVIDIA Jetson Orin Nano | — |
| Motor Driver | 2× BTS7960B H-Bridge | Pico 2W → USB serial (`/dev/ttyACM0`) |
| Microcontroller | Raspberry Pi Pico 2W | MicroPython, USB to Jetson |
| LiDAR | RPLiDAR A1M8 | USB serial (`/dev/ttyUSB0`) |
| IMU | MPU9250 | I2C bus 1, address `0x68` |
| Camera | IMX219-83 Stereo | CSI → V4L2 (`/dev/video0`, `/dev/video1`) |

---

## 1. Prerequisites

### 1.1 Jetson Orin Nano Setup

- **JetPack 6.x** (L4T R36.x, Ubuntu 22.04 based) flashed via NVIDIA SDK Manager
- Docker + NVIDIA Container Toolkit:
  ```bash
  # Docker is usually pre-installed on JetPack — verify:
  docker --version
  
  # Install NVIDIA Container Toolkit if not present:
  sudo apt-get install -y nvidia-container-toolkit
  sudo systemctl restart docker
  ```
- Add your user to the docker group:
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

### 1.2 Clone the Repository

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/<your-org>/HelMoRo-software-ROS2.git
cd HelMoRo-software-ROS2
```

---

## 2. Flash the Pico 2W Firmware

The Pico 2W runs MicroPython and handles motor PID control + encoder reading. **This must be done before running the robot.**

### 2.1 Install MicroPython on Pico 2W

1. Hold the **BOOTSEL** button on the Pico 2W and connect it via USB to your computer
2. Download the MicroPython `.uf2` from [micropython.org/download/RPI_PICO2_W](https://micropython.org/download/RPI_PICO2_W/)
3. Copy the `.uf2` file to the `RPI-RP2` USB drive that appears
4. The Pico will reboot automatically

### 2.2 Upload the Motor Controller Firmware

Using `mpremote`:
```bash
pip install mpremote
mpremote connect /dev/ttyACM0 cp \
  helmoro_base/helmoro_real/helmoro_motor_driver/firmware/pico_motor_controller.py \
  :main.py
mpremote connect /dev/ttyACM0 reset
```

Or use **Thonny IDE** — open `pico_motor_controller.py` and save it to the Pico as `main.py`.

### 2.3 Wiring (BTS7960B + Encoders → Pico 2W)

```
 Pico 2W                    BTS7960B (Left)         BTS7960B (Right)
┌──────────┐               ┌─────────────┐         ┌─────────────┐
│ GP0  ────┼──── RPWM ────►│  RPWM       │         │  RPWM       │◄──── RPWM ──── GP4
│ GP1  ────┼──── LPWM ────►│  LPWM       │         │  LPWM       │◄──── LPWM ──── GP5
│ GP2  ────┼──── R_EN ────►│  R_EN       │         │  R_EN       │◄──── R_EN ──── GP6
│ GP3  ────┼──── L_EN ────►│  L_EN       │         │  L_EN       │◄──── L_EN ──── GP7
│          │               │             │         │             │
│ GP10 ────┼──── ENC_A ◄───│ Left Enc A  │         │ Right Enc A │───► ENC_A ──── GP12
│ GP11 ────┼──── ENC_B ◄───│ Left Enc B  │         │ Right Enc B │───► ENC_B ──── GP13
│          │               └─────────────┘         └─────────────┘
│ GND  ────┼──── GND (shared with BTS7960B + encoders)
│ VBUS ────┼──── 5V to encoder VCC
│ USB  ────┼──── USB cable to Jetson (/dev/ttyACM0)
└──────────┘

Motor Power: Battery (6–27V) → BTS7960B VCC/GND → B+/B- to motors
```

---

## 3. Sensor Verification (Before First Run)

Run these checks on the Jetson **before launching the full stack**. You can do them natively or inside the Docker container.

### 3.1 MPU9250 IMU — I2C Check

```bash
sudo apt-get install -y i2c-tools
i2cdetect -y 1
```
You should see `68` at row 60, col 8. If you wired AD0 high, it will be `69` — update `i2c_address` in `config/mpu9250_params_i2c.yaml`.

### 3.2 RPLiDAR A1M8 — USB Check

```bash
ls -la /dev/ttyUSB0
# Grant access if needed:
sudo chmod 666 /dev/ttyUSB0
```

### 3.3 Pico 2W — USB Serial Check

```bash
ls -la /dev/ttyACM0
# Quick test (should return JSON with encoder data):
python3 -c "
import serial, json
s = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
s.write(json.dumps({'cmd': [0.0, 0.0]}).encode() + b'\n')
print(s.readline().decode())
s.close()
"
```

### 3.4 IMX219-83 Stereo Camera — V4L2 Check

```bash
sudo apt-get install -y v4l-utils
v4l2-ctl --list-devices
# Should list /dev/video0 and /dev/video1

# Test left camera:
v4l2-ctl -d /dev/video0 --all | head -20
```

> **Note:** On Jetson with CSI cameras, the device indices can change. Check which `/dev/videoX` corresponds to which camera and update `stereo_camera_launch.py` arguments if needed:
> ```bash
> ros2 launch helmoro_real_bringup stereo_camera_launch.py left_device:=/dev/video0 right_device:=/dev/video1
> ```

---

## 4. Stereo Camera Calibration

**Required for depth/pointcloud.** Without calibration, `stereo_image_proc` cannot compute disparity.

### 4.1 Print a Calibration Target

Print a **checkerboard pattern** (9×6 inner corners, 25mm squares). Keep it flat — tape it to cardboard.

### 4.2 Run the Calibration Tool

```bash
# First, launch only the cameras:
ros2 launch helmoro_real_bringup stereo_camera_launch.py

# In another terminal, run the calibrator:
ros2 run camera_calibration cameracalibrator \
  --size 9x6 \
  --square 0.025 \
  --approximate 0.1 \
  right:=/sensors/camera/right/image_raw \
  left:=/sensors/camera/left/image_raw \
  left_camera:=/sensors/camera/left \
  right_camera:=/sensors/camera/right
```

### 4.3 Calibration Steps

1. Hold the checkerboard in front of both cameras
2. Move it around — cover all areas: left, right, top, bottom, tilted, close, far
3. The progress bars (X, Y, Size, Skew) should all turn green
4. Click **CALIBRATE** → wait for computation
5. Click **SAVE** → writes calibration YAML files
6. Click **COMMIT** → the camera nodes reload calibration automatically

The calibration files are saved to `~/.ros/camera_info/`. On subsequent launches, `v4l2_camera` loads them automatically.

---

## 5. Measure & Update Robot Geometry

The defaults may not match your actual robot. **Measure and update these values:**

### 5.1 Wheel Parameters

Measure on your robot:
- **Wheel radius:** Measure the wheel diameter with calipers, divide by 2
- **Wheel separation:** Measure center-to-center distance between left and right wheels

Update in **two places**:

1. **ROS side** — `helmoro_base/helmoro_real/helmoro_motor_driver/config/motor_params.yaml`:
   ```yaml
   wheel_separation: 0.195   # ← your measured value in meters
   wheel_radius: 0.045       # ← your measured value in meters
   ```

2. **Pico firmware** — `helmoro_base/helmoro_real/helmoro_motor_driver/firmware/pico_motor_controller.py`:
   ```python
   WHEEL_RADIUS = 0.045      # ← must match the ROS config
   ```

3. **URDF** — `helmoro_base/helmoro_common/helmoro_description/urdf/helmoro_parameters.urdf`:
   Update any wheel radius/separation xacro properties to match

### 5.2 Encoder CPR (Counts Per Revolution)

In the Pico firmware, set `ENCODER_CPR` to your motor's encoder specification. This is typically printed on the motor datasheet. Common values: 330, 660, 1320 for geared motors.

---

## 6. PID Tuning

The Pico firmware has PID constants that need tuning for your specific motors.

### 6.1 Start Conservative

Edit `pico_motor_controller.py` on the Pico:
```python
KP = 1.0
KI = 0.0
KD = 0.0
```

### 6.2 Tuning Procedure

1. Launch the robot stack
2. Send a slow velocity command:
   ```bash
   ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
     "{linear: {x: 0.1}, angular: {z: 0.0}}" -r 10
   ```
3. Monitor odometry:
   ```bash
   ros2 topic echo /motors/odom --field twist.twist.linear.x
   ```
4. **KP:** Increase until the wheel tracks the command without oscillation
5. **KI:** Add small values (0.1, 0.2…) to eliminate steady-state error
6. **KD:** Add small values (0.01, 0.02…) to reduce overshoot

After modifying, re-upload:
```bash
mpremote connect /dev/ttyACM0 cp pico_motor_controller.py :main.py
mpremote connect /dev/ttyACM0 reset
```

---

## 7. IMU Calibration

### 7.1 Gyroscope & Accelerometer Bias

1. Place the robot on a **flat, stationary surface**
2. Launch only the IMU:
   ```bash
   ros2 launch helmoro_real_bringup imu_launch.py
   ```
3. Record ~10 seconds of data:
   ```bash
   ros2 topic echo /sensors/imu/data --field linear_acceleration
   ros2 topic echo /sensors/imu/data --field angular_velocity
   ```
4. Average the values. Ideally:
   - `linear_acceleration`: `[0, 0, 9.81]`
   - `angular_velocity`: `[0, 0, 0]`
5. Compute offsets (expected − measured) and set in `config/mpu9250_params_i2c.yaml`:
   ```yaml
   acceleration_bias: [0.0, 0.0, 0.0]   # ← fill in offsets
   gyroscope_bias: [0.0, 0.0, 0.0]      # ← fill in offsets
   ```

---

## 8. Build & Run with Docker

### 8.1 Build the Jetson Image

```bash
cd ~/ros2_ws/src/HelMoRo-software-ROS2
docker/build.sh jetson
```

This builds `helmoro:jetson` using `docker/Dockerfile.jetson`. Takes ~15–30 min on the first build.

### 8.2 Launch the Full Robot Stack

```bash
cd docker
docker compose -f docker-compose.jetson.yaml up
```

This starts **all nodes**: motors, IMU, LiDAR, cameras, SLAM, navigation, EKF, controller.

### 8.3 Open Additional Terminals

```bash
# Attach a new shell to the running container:
docker exec -it helmoro_jetson bash

# Inside the container, everything is sourced:
ros2 topic list
ros2 topic echo /sensors/imu/data
ros2 topic echo /motors/odom
ros2 launch helmoro_common_bringup rviz_launch.py  # (if display connected)
```

### 8.4 Using tmux Inside the Container

```bash
docker exec -it helmoro_jetson tmux
# Ctrl+B then C → new window
# Ctrl+B then N → next window
# Ctrl+B then P → previous window
```

---

## 9. Running Without Docker (Native)

If you prefer to run natively on the Jetson:

### 9.1 Install ROS 2 Humble

Follow the [official install guide](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html).

### 9.2 Install Dependencies

```bash
sudo apt install -y \
  ros-humble-ros2-control \
  ros-humble-ros2-controllers \
  ros-humble-diff-drive-controller \
  ros-humble-joint-state-broadcaster \
  ros-humble-slam-toolbox \
  ros-humble-robot-localization \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-twist-mux \
  ros-humble-topic-tools \
  ros-humble-v4l2-camera \
  ros-humble-stereo-image-proc \
  ros-humble-image-pipeline \
  ros-humble-camera-calibration \
  python3-serial \
  i2c-tools

# Clone external drivers into workspace:
cd ~/ros2_ws/src
git clone https://github.com/hiwad-aziz/ros2_mpu9250_driver.git mpu9250driver
git clone https://github.com/Slamtec/rplidar_ros.git -b ros2
```

### 9.3 Build & Launch

```bash
cd ~/ros2_ws
colcon build --symlink-install --packages-ignore helmoro_sim_bringup helmoro_gazebo_tools helmoro_motors
source install/setup.bash
ros2 launch helmoro_real_bringup helmoro_launch.py
```

---

## 10. Verifying the Running System

Once launched, verify each subsystem:

| Check | Command | Expected |
|-------|---------|----------|
| All nodes alive | `ros2 node list` | 15+ nodes listed |
| IMU data | `ros2 topic hz /sensors/imu/data` | ~100 Hz |
| LiDAR scan | `ros2 topic hz /scan` | ~5–10 Hz |
| Motor odometry | `ros2 topic hz /motors/odom` | ~20 Hz |
| Camera images | `ros2 topic hz /sensors/camera/left/image_raw` | ~30 Hz |
| EKF output | `ros2 topic hz /odometry/filtered` | ~30 Hz |
| SLAM map | `ros2 topic echo /map --once` | OccupancyGrid with data |
| Nav2 status | `ros2 topic echo /bt_navigator/transition_event` | Active state |
| TF tree | `ros2 run tf2_tools view_frames` | Generates frames.pdf |

---

## 11. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `/dev/ttyACM0` not found | Pico not connected or no firmware | Re-plug USB, re-flash firmware |
| `/dev/ttyUSB0` not found | LiDAR not connected | Check USB cable, `dmesg \| tail` |
| `i2cdetect` shows nothing at 0x68 | IMU wiring issue | Check SDA→GP2, SCL→GP3 on Jetson I2C bus 1 |
| Camera shows 0 Hz | CSI ribbon cable loose | Reseat cable, check `v4l2-ctl --list-devices` |
| Robot drives in circles | Wheel params wrong | Measure and update `wheel_separation` |
| EKF diverges | IMU not calibrated | Run IMU calibration (Section 7) |
| No depth/pointcloud | Camera not calibrated | Run stereo calibration (Section 4) |
| Motor PID oscillation | Gains too high | Reduce KP, set KI/KD to 0, retune |
| Permission denied on devices | User not in dialout/i2c group | `sudo usermod -aG dialout,i2c $USER` |
| Docker build fails on Jetson | Wrong L4T version | Check `cat /etc/nv_tegra_release` and update `L4T_VERSION` in Dockerfile.jetson |

---

## 12. External Repositories Used

| Repository | What For | Cloned Automatically in Docker |
|------------|----------|-------------------------------|
| [hiwad-aziz/ros2_mpu9250_driver](https://github.com/hiwad-aziz/ros2_mpu9250_driver) | MPU9250 IMU driver (I2C) | Yes |
| [Slamtec/rplidar_ros](https://github.com/Slamtec/rplidar_ros) (`humble` branch) | RPLiDAR A1M8 driver | Yes |

No external repo is needed for the stereo camera — it uses standard `ros-humble-v4l2-camera` and `ros-humble-stereo-image-proc` from apt.

---

## 13. System Architecture

### 13.1 Flowchart

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        JETSON ORIN NANO                                 │
│                                                                         │
│  ┌───────────────────── SENSOR LAYER ─────────────────────────────┐    │
│  │                                                                 │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │    │
│  │  │  MPU9250 IMU │  │ RPLiDAR A1M8 │  │ IMX219-83 Stereo   │   │    │
│  │  │   (I2C)      │  │   (USB)      │  │    (CSI×2)         │   │    │
│  │  └──────┬───────┘  └──────┬───────┘  └───┬────────┬───────┘   │    │
│  │         │                  │               │        │           │    │
│  │  mpu9250driver      rplidar_ros     v4l2_camera  v4l2_camera   │    │
│  │         │                  │            (left)     (right)      │    │
│  │         ▼                  ▼               │        │           │    │
│  │  /sensors/imu/data    /scan                ▼        ▼           │    │
│  │                                   stereo_image_proc             │    │
│  │                                      │         │                │    │
│  │                                 /disparity  /points2            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────────── MOTOR LAYER ──────────────────────────────┐    │
│  │                                                                 │    │
│  │  ┌─────────────────────┐        USB Serial (JSON)              │    │
│  │  │ helmoro_motor_driver│ ◄──────────────────────►  ┌────────┐  │    │
│  │  │    (ROS 2 Node)     │  {"cmd":[v_l, v_r]}       │Pico 2W │  │    │
│  │  │                     │  {"enc":[],  "vel":[]}     │        │  │    │
│  │  │ Subscribes:         │                            │  PID   │  │    │
│  │  │  /cmd_vel           │                            │ Control│  │    │
│  │  │ Publishes:          │                            │  50 Hz │  │    │
│  │  │  /motors/odom       │                            └───┬┬───┘  │    │
│  │  │  /joint_states      │                                ││      │    │
│  │  └─────────────────────┘                           ┌────┘└────┐ │    │
│  │                                                    ▼          ▼ │    │
│  │                                              BTS7960B    BTS7960B    │
│  │                                              (Left)      (Right)    │
│  │                                                │            │       │
│  │                                            Left Motor  Right Motor  │
│  │                                            + Encoder   + Encoder    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────── STATE ESTIMATION LAYER ───────────────────────┐    │
│  │                                                                 │    │
│  │              ┌──────────────────────┐                           │    │
│  │              │  EKF (robot_         │                           │    │
│  │              │  localization)       │                           │    │
│  │              │  30 Hz, 2D mode      │                           │    │
│  │              │                      │                           │    │
│  │  /motors/odom ──►│  Fuses:          │                           │    │
│  │  (wheel odom)    │  • Wheel linear  │──► /odometry/filtered     │    │
│  │                   │    velocity (vx) │──► TF: odom → base_link  │    │
│  │  /sensors/imu/ ──►│  • IMU yaw rate │                           │    │
│  │   data            │    (vyaw)       │                           │    │
│  │              └──────────────────────┘                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────── SLAM & NAVIGATION LAYER ──────────────────────┐    │
│  │                                                                 │    │
│  │  ┌─────────────────┐       ┌──────────────────────────────┐    │    │
│  │  │  SLAM Toolbox   │       │        Nav2 Stack            │    │    │
│  │  │  (sync mode)    │       │                              │    │    │
│  │  │                 │       │  ┌────────┐  ┌───────────┐   │    │    │
│  │  │ /scan ──► Map   │       │  │Planner │  │Controller │   │    │    │
│  │  │ /odom ──► Build │       │  │(NavFn) │  │ (MPPI)    │   │    │    │
│  │  │                 │       │  └───┬────┘  └─────┬─────┘   │    │    │
│  │  │ Publishes:      │       │      │             │         │    │    │
│  │  │  /map           │──────►│  Global Path  Local Control  │    │    │
│  │  │  TF: map→odom   │       │      │             │         │    │    │
│  │  └─────────────────┘       │      └──────┬──────┘         │    │    │
│  │                            │             ▼                │    │    │
│  │                            │         /cmd_vel             │    │    │
│  │                            └──────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────────── CONTROL & COMMON LAYER ───────────────────────┐    │
│  │                                                                 │    │
│  │  twist_mux                    ros2_control                      │    │
│  │  ┌──────────┐           ┌───────────────────────┐              │    │
│  │  │ Priority │           │ diff_drive_controller  │              │    │
│  │  │ 1: /joy  │──►        │  (100 Hz update)      │              │    │
│  │  │ 2: /nav  │──► /cmd_vel   │                    │              │    │
│  │  └──────────┘           │  Wheel kinematics:     │              │    │
│  │                         │  v_L = vx − wz×d/2     │              │    │
│  │  robot_state_publisher  │  v_R = vx + wz×d/2     │              │    │
│  │  ┌──────────────────┐   └───────────────────────┘              │    │
│  │  │ URDF → TF tree   │                                          │    │
│  │  │ base_link, wheels,│                                          │    │
│  │  │ imu_link, lidar.. │                                          │    │
│  │  └──────────────────┘                                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 13.2 Explanation

#### Sensor Layer
- **MPU9250 IMU** connects via I2C (bus 1, address 0x68). The `mpu9250driver` node reads accelerometer and gyroscope data at 100 Hz and publishes to `/sensors/imu/data`.
- **RPLiDAR A1M8** connects via USB serial. The `rplidar_ros` driver publishes laser scans to `/scan` (360° at 5–10 Hz, range 0.2–12m).
- **IMX219-83 Stereo Camera** has two CSI lenses appearing as `/dev/video0` and `/dev/video1`. Two `v4l2_camera` nodes publish raw images, and `stereo_image_proc` computes disparity maps and 3D point clouds from the stereo pair.

#### Motor Layer
- **helmoro_motor_driver** is the ROS 2 node running on the Jetson. It receives `/cmd_vel` commands and converts them to left/right wheel velocities using differential drive kinematics.
- It communicates with the **Pico 2W** over USB serial using a JSON protocol: sends velocity commands `{"cmd": [v_left, v_right]}` and receives encoder positions + measured velocities.
- The **Pico 2W** runs a 50 Hz PID control loop that drives the **BTS7960B H-Bridges** via PWM and reads quadrature **encoders** via interrupt-driven counting.
- The ROS node publishes wheel odometry to `/motors/odom` and joint states to `/joint_states`.

#### State Estimation Layer
- **robot_localization EKF** fuses two inputs at 30 Hz in 2D mode:
  - Wheel odometry (`/motors/odom`) — provides linear velocity (vx)
  - IMU (`/sensors/imu/data`) — provides yaw rate (angular velocity z)
- Outputs a filtered odometry estimate on `/odometry/filtered` and broadcasts the `odom → base_link` transform.

#### SLAM & Navigation Layer
- **SLAM Toolbox** (synchronous mode) builds an occupancy grid map from LiDAR scans and odometry. Publishes `/map` and the `map → odom` transform. Resolution: 5cm, laser range: 0.2–12m.
- **Nav2** provides autonomous navigation:
  - **NavFn Planner** computes global paths on the SLAM map
  - **MPPI Controller** generates smooth local velocity commands (max 0.5 m/s)
  - **Behavior Tree** handles recovery behaviors: spin, backup, wait
  - Costmaps use the LiDAR scan and the static map for obstacle avoidance

#### Control & Common Layer
- **twist_mux** prioritizes velocity sources: joystick (priority 1) overrides navigation (priority 2). Outputs the winning command on `/cmd_vel`.
- **diff_drive_controller** (ros2_control) handles wheel kinematics at 100 Hz: converts twist commands into individual wheel velocity targets.
- **robot_state_publisher** reads the URDF model and publishes the full TF tree (base_link, wheel frames, imu_link, laser_frame, camera frames).

#### Data Flow Summary

```
Joystick/Nav2 → twist_mux → /cmd_vel → diff_drive_controller
    → motor_driver_node → USB JSON → Pico 2W → BTS7960B PWM → Motors
    
Motors → Encoders → Pico 2W → USB JSON → motor_driver_node → /motors/odom
                                                                    ↓
IMU → mpu9250driver → /sensors/imu/data ─────────────────────►  EKF
                                                                    ↓
                                                          /odometry/filtered
                                                                    ↓
LiDAR → rplidar_ros → /scan ──────────────────────────►  SLAM Toolbox → /map
                                                                    ↓
                                                              Nav2 → /cmd_vel
```

#### TF Tree

```
map
 └── odom                    (SLAM Toolbox)
      └── base_link          (EKF)
           ├── imu_link
           ├── laser_frame
           ├── camera_link
           │    ├── camera_left_optical_frame
           │    └── camera_right_optical_frame
           ├── front_left_wheel
           ├── front_right_wheel
           ├── rear_left_wheel
           └── rear_right_wheel
```
