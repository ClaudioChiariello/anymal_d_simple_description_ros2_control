import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution, PythonExpression, TextSubstitution, FindExecutable

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from ament_index_python.packages import get_package_share_directory
from launch.actions import RegisterEventHandler, TimerAction, Shutdown
from launch.event_handlers import OnProcessStart
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.parameter_descriptions import ParameterValue, ParameterFile


def generate_launch_description():

    nodes = []
    anymal_description_pkg = get_package_share_directory('anymal_d_simple_description')
    xacro_file = os.path.join(anymal_description_pkg, 'urdf', 'anymal_d_ros2_control.xacro') # Ensure it uses xacro file

    # Run the xacro command to convert the xacro file into an urdf to pass then to robot_description
    robot_description_content = Command([
        FindExecutable(name="xacro"),
        " ",
        xacro_file,
    ])

    # Start gz-sim
    gz_launch_path = os.path.join(
        get_package_share_directory('ros_gz_sim'),
        'launch',
        'gz_sim.launch.py'
    )

    gz_sim_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch_path),
        launch_arguments={
            'gz_args': [LaunchConfiguration('world_file'), ' -r'],
            'on_exit_shutdown': 'True'
        }.items(),
    )

    # ros2_control node with MuJoCo. Nota che lo stesso eseguibile del pacchetto controller_manager. Per gz sim devi lanciarlo da xml
    nodes.append(
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{
                "robot_description": ParameterValue(robot_description_content, value_type=str),
                "use_sim_time": LaunchConfiguration("use_sim_time")
            }],
        ),
    
    )

    nodes.append(
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-topic", "robot_description",
                "-name", "anymal_d",
                "-allow_renaming", "false",
                "-x", "0.0",
                "-y", "0.0",
                "-z", "0.92",
                "-Y", "0.0"
            ]
        )
    )

    nodes.append(
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry',
                '/imu/data@sensor_msgs/msg/Imu@gz.msgs.IMU',
            ],
            output='screen'
        )
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    ) #among the controller of controller_manager you are saying to launchg the joint_state_broadcaster

    joint_trajectory_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller", "--controller-manager", "/controller_manager"],  
    ) 

    joint_pos_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["position_controller", "--controller-manager", "/controller_manager"],  
    ) 

    controllers = [
        joint_state_broadcaster, 
        joint_trajectory_controller,
        joint_pos_controller
    ]


    return LaunchDescription([

        DeclareLaunchArgument('world_file', default_value='empty.sdf'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        gz_sim_include,
        *nodes, 
        *controllers        
    ]
)



