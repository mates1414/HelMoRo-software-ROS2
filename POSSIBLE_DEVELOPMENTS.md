# HelMoRo — Possible Developments for Senior Design Project

## Navigation & Planning

1. **Multi-goal waypoint navigation** — Add a custom waypoint following interface (RViz panel or web UI) for patrol/inspection routes
2. **Dynamic obstacle avoidance** — Integrate depth camera data into the local costmap (currently only LiDAR is used)
3. **Map saving & loading** — Add a launch option to switch SLAM between mapping mode and localization-on-saved-map mode (currently always mapping)
4. **Outdoor navigation** — Add GPS waypoint navigation using `robot_localization`'s `navsat_transform_node`
5. **Multi-floor navigation** — Elevator detection + map switching for multi-level environments

## Perception

6. **Object detection** — Add a YOLOv8/RT-DETR node using the RGB camera for real-time object detection
7. **Person following** — Combine object detection + Nav2 to follow a detected person
8. **3D mapping** — Use the depth camera with `rtabmap_ros` for 3D SLAM instead of 2D-only slam_toolbox
9. **ArUco/AprilTag detection** — Add fiducial marker detection for precision docking or localization
10. **Semantic costmap layer** — Classify terrain/obstacles and assign different costs

## Autonomy & Behavior

11. **Behavior trees for missions** — Create custom BT nodes for complex autonomous tasks (inspect, deliver, patrol)
12. **Auto-docking/charging** — Implement autonomous return-to-charger using visual markers
13. **Coverage path planning** — Add a coverage planner for floor cleaning/inspection scenarios
14. **Fleet management** — Multi-robot coordination using namespaces (already partially supported)

## User Interface

15. **Web-based dashboard** — Build a `rosbridge` + web UI (React/Vue) for remote monitoring and control
16. **Android/iOS joystick app** — Replace physical joystick with a mobile phone controller
17. **RViz custom panels** — Add mission control panels, battery status, diagnostics display
18. **Voice control** — Add speech recognition node for voice-commanded navigation

## Hardware Integration

19. **Robotic arm integration** — Mount a manipulator for pick-and-place tasks (MoveIt 2)
20. **Additional sensors** — Add ultrasonic sensors for close-range obstacle detection or a thermal camera
21. **LED status indicators** — Add an LED strip controlled via ROS for robot state feedback
22. **Battery monitoring node** — Publish battery state via `sensor_msgs/BatteryState`

## Software Quality

23. [x] **Docker containerization** — Create Dockerfiles for reproducible builds (sim + real)
24. **CI/CD pipeline** — GitHub Actions for automated build, test, and linting
25. **ROS 2 launch testing** — Add `launch_testing` integration tests for the full stack
26. **Parameter tuning framework** — Dynamic reconfigure for PID, Nav2, and SLAM parameters at runtime
27. **Simulation-to-real transfer** — Domain randomization in Gazebo for training models that transfer to real hardware

## Machine Learning

28. **Reinforcement learning navigation** — Train an RL agent in Gazebo to replace/augment Nav2's local planner
29. **Visual SLAM** — Replace LiDAR SLAM with ORB-SLAM3 or Stella-VSLAM using the camera
30. **Anomaly detection** — Use sensor data to detect abnormal environments (gas leak, temperature, etc.)

---

## Recommended High-Impact Choices

| # | Development | Why |
|---|-------------|-----|
| 6+7 | Object detection + person following | Visually impressive, uses existing camera |
| 15 | Web dashboard | Great for demos, shows full-stack skills |
| 13 | Coverage path planning | Practical application (cleaning/inspection), publishable |
| 8 | 3D SLAM with depth camera | Depth camera hardware already present but unused for mapping |
