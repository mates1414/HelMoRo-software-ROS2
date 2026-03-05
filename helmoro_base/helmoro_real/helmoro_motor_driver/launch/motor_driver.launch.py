#!/usr/bin/env python3
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    pkg_motor_driver = get_package_share_directory('helmoro_motor_driver')

    config = PathJoinSubstitution([pkg_motor_driver, 'config', 'motor_params.yaml'])

    motor_driver = Node(
        package='helmoro_motor_driver',
        executable='motor_driver_node',
        name='helmoro_motor_driver_node',
        parameters=[config],
        output='screen',
    )

    ld = LaunchDescription()
    ld.add_action(motor_driver)
    return ld
