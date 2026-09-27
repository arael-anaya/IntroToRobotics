import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('fourWheelRobot')
    world = os.path.join(pkg, 'worlds' , 'my_world.sdf')
    urdf = os.path.join(pkg, 'urdf', 'my_robot.urdf')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch' , 'gz_sim.launch.py')),
        launch_arguments = {'gz_args': f'-r {world}'}.items())

    spawn = Node(
            package='ros_gz_sim', executable='create',
            arguments=['-file', urdf, '-name' , 'my_robot' , '-z' , '0.1'],
            output='screen')
    
    bridge = Node(
        package = 'ros_gz_bridge' , executable='parameter_bridge',
        arguments =['/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist'],
        output = 'screen')

    follow_cam = ExecuteProcess(
        cmd=['python3', os.path.join(pkg, 'scripts', 'follow_cam.py'), 'my_robot'],
        output='screen')

    trail = ExecuteProcess(
        cmd=['python3', os.path.join(pkg, 'scripts', 'trail.py'), 'my_robot'],
        output='screen')

    return LaunchDescription([gazebo, spawn, bridge, follow_cam, trail])


    
    
    
    

    