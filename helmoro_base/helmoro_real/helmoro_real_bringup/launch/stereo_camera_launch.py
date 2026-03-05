#!/usr/bin/env python3
"""
IMX219-83 Stereo Camera Launch

Launches:
  1. Left camera  (v4l2_camera) → /sensors/camera/left/image_raw
  2. Right camera (v4l2_camera) → /sensors/camera/right/image_raw
  3. stereo_image_proc           → /sensors/camera/depth, /sensors/camera/points2

The IMX219-83 stereo module has two CSI cameras on the Jetson Orin Nano.
They appear as /dev/video0 and /dev/video1 (adjust if different).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


ARGUMENTS = [
    DeclareLaunchArgument('left_device', default_value='/dev/video0',
                          description='Left camera V4L2 device'),
    DeclareLaunchArgument('right_device', default_value='/dev/video1',
                          description='Right camera V4L2 device'),
    DeclareLaunchArgument('image_width', default_value='640'),
    DeclareLaunchArgument('image_height', default_value='480'),
    DeclareLaunchArgument('framerate', default_value='30.0'),
    DeclareLaunchArgument('camera_frame', default_value='camera_link'),
]


def generate_launch_description():

    # ── Left Camera Node ─────────────────────────────────────────────
    left_camera = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='left_camera',
        namespace='sensors/camera/left',
        parameters=[{
            'video_device': LaunchConfiguration('left_device'),
            'image_size': [
                LaunchConfiguration('image_width'),
                LaunchConfiguration('image_height'),
            ],
            'camera_frame_id': 'camera_left_optical_frame',
            'pixel_format': 'YUYV',
        }],
        remappings=[
            ('image_raw', 'image_raw'),
            ('camera_info', 'camera_info'),
        ],
        output='screen',
    )

    # ── Right Camera Node ────────────────────────────────────────────
    right_camera = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='right_camera',
        namespace='sensors/camera/right',
        parameters=[{
            'video_device': LaunchConfiguration('right_device'),
            'image_size': [
                LaunchConfiguration('image_width'),
                LaunchConfiguration('image_height'),
            ],
            'camera_frame_id': 'camera_right_optical_frame',
            'pixel_format': 'YUYV',
        }],
        remappings=[
            ('image_raw', 'image_raw'),
            ('camera_info', 'camera_info'),
        ],
        output='screen',
    )

    # ── Stereo Image Processing (disparity → depth + pointcloud) ─────
    stereo_proc = ComposableNodeContainer(
        name='stereo_image_proc_container',
        namespace='sensors/camera',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[
            ComposableNode(
                package='stereo_image_proc',
                plugin='stereo_image_proc::DisparityNode',
                name='disparity_node',
                namespace='sensors/camera',
                remappings=[
                    ('left/image_rect', 'left/image_raw'),
                    ('left/camera_info', 'left/camera_info'),
                    ('right/image_rect', 'right/image_raw'),
                    ('right/camera_info', 'right/camera_info'),
                ],
                parameters=[{
                    'approximate_sync': True,
                    'stereo_algorithm': 0,           # 0=BM, 1=SGBM
                    'disparity_range': 64,
                    'texture_threshold': 10,
                    'speckle_size': 100,
                    'speckle_range': 4,
                    'min_disparity': 0,
                    'uniqueness_ratio': 15.0,
                    'P1': 200.0,
                    'P2': 400.0,
                }],
            ),
            ComposableNode(
                package='stereo_image_proc',
                plugin='stereo_image_proc::PointCloudNode',
                name='point_cloud_node',
                namespace='sensors/camera',
                remappings=[
                    ('left/image_rect_color', 'left/image_raw'),
                    ('left/camera_info', 'left/camera_info'),
                    ('right/camera_info', 'right/camera_info'),
                ],
                parameters=[{
                    'approximate_sync': True,
                    'use_color': True,
                }],
            ),
        ],
        output='screen',
    )

    ld = LaunchDescription(ARGUMENTS)
    ld.add_action(left_camera)
    ld.add_action(right_camera)
    ld.add_action(stereo_proc)
    return ld
