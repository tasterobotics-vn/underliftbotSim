from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, OpaqueFunction
from launch_ros.actions import Node


def generate_launch_description():
    
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="True",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ]
    )

    wheel_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["underliftbot_controller", 
                   "--controller-manager", 
                   "/controller_manager"
        ]
    )

    wheel_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'underliftbot_controller',
            '--controller-manager', 
            '/controller_manager',
            '--controller-ros-args',
            '-r /underliftbot_controller/cmd_vel:=/cmd_vel',
            '--controller-ros-args',
            '-r /underliftbot_controller/odom:=/odom'
        ],
    )

    lift_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "lift_position_controller",
            "--controller-manager",
            "/controller_manager",
        ],
    )

    gz_convert = Node(
        package="underliftbot_controller",
        executable="gz_convert",
        name="gz_convert"
    )

    return LaunchDescription(
        [
            use_sim_time_arg,
            joint_state_broadcaster_spawner,
            wheel_controller_spawner,
            lift_controller_spawner,
            gz_convert
        ]
    )