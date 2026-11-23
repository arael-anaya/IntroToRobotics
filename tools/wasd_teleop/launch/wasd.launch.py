from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Raw keyboard input needs a real terminal, so this opens its own xterm.
    # If you don't have xterm, use `ros2 run wasd_teleop wasd` instead.
    return LaunchDescription([
        DeclareLaunchArgument('topic', default_value='cmd_vel'),
        DeclareLaunchArgument('linear', default_value='0.5'),
        DeclareLaunchArgument('angular', default_value='1.0'),
        DeclareLaunchArgument('hold_timeout', default_value='0.55'),
        Node(
            package='wasd_teleop',
            executable='wasd',
            name='wasd_teleop',
            prefix='xterm -e',
            parameters=[{
                'topic': LaunchConfiguration('topic'),
                'linear': LaunchConfiguration('linear'),
                'angular': LaunchConfiguration('angular'),
                'hold_timeout': LaunchConfiguration('hold_timeout'),
            }],
        ),
    ])
