import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution

from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    # Directories
    pkg_rplidar_ros = get_package_share_directory('rplidar_ros')

    # Paths — RPLiDAR A1M8
    rplidar_launch = PathJoinSubstitution([pkg_rplidar_ros, 'launch', 'rplidar_a1_launch.py'])

    # ROS2 RPLidar A1M8 Node
    rplidar_node = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([rplidar_launch]),
        launch_arguments=[
            ('frame_id', 'laser')]
    )

    rplidar_node_with_namespace = GroupAction(
     actions=[
         PushRosNamespace('sensors/lidar'),
         rplidar_node,
      ]
   )

    # Create launch description and add actions
    ld = LaunchDescription()
    ld.add_action(rplidar_node_with_namespace)
    return ld