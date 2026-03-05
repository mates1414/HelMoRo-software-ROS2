#!/usr/bin/env python3

# Launch MPU9250 IMU Driver (I2C)

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node

def generate_launch_description():
    # Directories
    pkg_helmoro_real_bringup = get_package_share_directory('helmoro_real_bringup')

    # Paths
    mpu9250_config = PathJoinSubstitution([pkg_helmoro_real_bringup, 'config', 'mpu9250_params_i2c.yaml'])

    # ROS2 MPU9250 IMU Node
    # Publishes: /imu/data (sensor_msgs/Imu), /imu/mag (sensor_msgs/MagneticField)
    mpu9250 = Node(
        package='mpu9250driver',
        executable='mpu9250driver',
        name='mpu9250driver_node',
        namespace='sensors/imu',
        parameters=[mpu9250_config],
        remappings=[
            ('imu', 'data'),        # remap to /sensors/imu/data
            ('mag', 'mag'),         # /sensors/imu/mag
        ],
        output='screen',
    )

    # Create launch description and add actions
    ld = LaunchDescription()
    ld.add_action(mpu9250)
    return ld