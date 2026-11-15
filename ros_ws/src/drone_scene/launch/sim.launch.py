"""Start the outdoor scene, drone, RGB-D cameras and ROS bridges."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('drone_scene')
    gz_share = get_package_share_directory('ros_gz_sim')
    description = ParameterValue(Command([
        'xacro ', os.path.join(share, 'urdf', 'drone_camera.xacro'),
    ]), value_type=str)
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='semantic_outdoor.sdf',
                              description='World filename in drone_scene/worlds'),
        DeclareLaunchArgument('gz_extra_args', default_value='',
                              description='Extra Gazebo args, e.g. -s --headless-rendering'),
        DeclareLaunchArgument('x', default_value='-5.0'),
        DeclareLaunchArgument('y', default_value='1.5'),
        DeclareLaunchArgument('z', default_value='0.15'),
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', os.pathsep.join([
            os.path.join(share, 'models'), os.path.dirname(share),
            os.environ.get('GZ_SIM_RESOURCE_PATH', ''),
        ])),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gz_share, 'launch', 'gz_sim.launch.py')),
            launch_arguments={
                'gz_args': ['-r -v 3 ', LaunchConfiguration('gz_extra_args'), ' "', PathJoinSubstitution([
                    share, 'worlds', LaunchConfiguration('world')]), '"'],
                'on_exit_shutdown': 'true',
            }.items(),
        ),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description, 'use_sim_time': True}],
             output='screen'),
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-world', 'e2es_indoor', '-name', 'semantic_drone',
                        '-topic', '/robot_description',
                        '-x', LaunchConfiguration('x'), '-y', LaunchConfiguration('y'),
                        '-z', LaunchConfiguration('z')]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': os.path.join(share, 'config', 'ros_gz_bridge.yaml'),
                          'use_sim_time': True}]),
    ])
