import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, UnsetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('fourWheelRobot')
    world = os.path.join(pkg, 'worlds' , 'my_world.sdf')
    urdf = os.path.join(pkg, 'urdf', 'my_robot.urdf')
    rviz_config = os.path.join(pkg, 'config', 'view.rviz')

    with open(urdf, 'r') as f:
        robot_description = f.read()

    # Private Gazebo transport partition for this launch only. Without it, a
    # Gazebo server left over from an earlier run shares the same world name and
    # its robots get drawn in this GUI too (duplicate tables/wheels).
    partition = f'fourWheelRobot_{os.getpid()}'
    partition_env = [SetEnvironmentVariable('IGN_PARTITION', partition),
                     SetEnvironmentVariable('GZ_PARTITION', partition)]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch' , 'gz_sim.launch.py')),
        launch_arguments = {'gz_args': f'-r {world}', 'on_exit_shutdown': 'true'}.items())

    # Force software rendering for gazebo only. The WSLg GPU passthrough's Mesa
    # d3d12 driver doesn't implement GL_ARB_copy_image, which ogre-next needs
    # (both the GUI's GL3PlusTextureGpu::copyTo and the gpu_lidar/camera
    # sensors' render thread hit this and abort). llvmpipe has that extension.
    # GALLIUM_DRIVER must be overridden (not LIBGL_ALWAYS_SOFTWARE) since
    # compose.yaml hardcodes GALLIUM_DRIVER=d3d12 for the whole container,
    # which otherwise wins. Unset right after so nothing else is affected.
    force_software_gl_on = SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe')
    force_software_gl_off = UnsetEnvironmentVariable('GALLIUM_DRIVER')

    spawn = Node(
            package='ros_gz_sim', executable='create',
            arguments=['-file', urdf, '-name' , 'my_robot' , '-z' , '0.1'],
            output='screen')
    
    bridge = Node(
        package = 'ros_gz_bridge' , executable='parameter_bridge',
        arguments =['/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
                    '/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan'],
        output = 'screen')

    # Black trail behind the robot + chase camera (press K in the sim window to toggle)
    helpers = Node(
        package='fourWheelRobot', executable='sim_helpers',
        arguments=['my_robot'],
        output='screen')

    # Publishes TF (incl. lidar_link) from the exact urdf spawned into Gazebo above,
    # so RViz can never disagree with what's actually in the sim.
    rsp = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen')

    # The wheel joints are continuous, so robot_state_publisher can't place them
    # in TF without a /joint_states source. We don't care about wheel spin for
    # RViz, just need something publishing so the wheel transforms exist.
    jsp = Node(
        package='joint_state_publisher', executable='joint_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen')

    rviz = Node(
        package='rviz2', executable='rviz2',
        arguments=['-d', rviz_config],
        output='screen')

    # Gazebo's gpu_lidar stamps /scan with its own scoped frame name
    # ("<model>/<link>/<sensor>"), which robot_state_publisher never publishes
    # (it only knows the URDF's plain "lidar_link"). Without this, RViz can
    # never find a transform for the scan and silently shows nothing.
    scan_frame_bridge = Node(
        package='tf2_ros', executable='static_transform_publisher',
        arguments=['--frame-id', 'lidar_link',
                   '--child-frame-id', 'my_robot/lidar_link/lidar'],
        output='screen')

    return LaunchDescription([*partition_env, force_software_gl_on, gazebo, force_software_gl_off,
                               spawn, bridge, helpers, rsp, jsp, rviz, scan_frame_bridge])


    
    
    
    

    