"""Start perception and flight control, optionally including the simulation."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, Shutdown
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """Expose separate person/car demonstrations through spawn coordinates."""
    scene_share = get_package_share_directory('drone_scene')
    control_share = get_package_share_directory('drone_control')
    config = PathJoinSubstitution([control_share, 'config', 'semantic.yaml'])
    return LaunchDescription([
        DeclareLaunchArgument('start_sim', default_value='true'),
        DeclareLaunchArgument('weights', description='Absolute path to local YOLO .pt weights'),
        DeclareLaunchArgument('world', default_value='semantic_outdoor.sdf'),
        DeclareLaunchArgument('gz_extra_args', default_value=''),
        DeclareLaunchArgument('x', default_value='-5.0'),
        DeclareLaunchArgument('y', default_value='1.5'),
        DeclareLaunchArgument('z', default_value='0.15'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([scene_share, 'launch', 'sim.launch.py'])),
            condition=IfCondition(LaunchConfiguration('start_sim')),
            launch_arguments={name: LaunchConfiguration(name)
                              for name in ('world', 'x', 'y', 'z', 'gz_extra_args')}.items()),
        Node(package='drone_control', executable='semantic_perception', output='screen',
             parameters=[config, {'weights': LaunchConfiguration('weights')}],
             on_exit=[Shutdown(reason='Perception process exited')]),
        Node(package='drone_control', executable='semantic_controller', output='screen',
             parameters=[config],
             on_exit=[Shutdown(reason='Controller process exited')]),
    ])
