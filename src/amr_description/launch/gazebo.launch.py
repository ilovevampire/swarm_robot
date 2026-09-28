#!/usr/bin/env python3
"""
gazebo.launch.py
=================
Brings up: Gazebo Harmonic (warehouse.sdf) -> spawns the AMR at
charging_bay_1 -> robot_state_publisher -> ros2_control controllers ->
sensor bridges -> a Twist->TwistStamped relay so plain teleop tools work.

Run with:
    ros2 launch amr_description gazebo.launch.py
"""

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory("amr_description")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    xacro_file = os.path.join(pkg_share, "urdf", "amr.urdf.xacro")
    world_file = os.path.join(pkg_share, "worlds", "warehouse.sdf")

    robot_description = ParameterValue(
        Command(["xacro ", xacro_file]), value_type=str
    )

    # -----------------------------------------------------------------
    # 1) Start Gazebo Harmonic with OUR warehouse world (not the
    #    built-in empty.sdf we used for manual testing).
    # -----------------------------------------------------------------
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-r {world_file}"}.items(),
    )

    # -----------------------------------------------------------------
    # 2) robot_state_publisher
    # -----------------------------------------------------------------
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description,
                     "use_sim_time": True}],
    )

    # -----------------------------------------------------------------
    # 3) Spawn at charging_bay_1 (-7.0, -5), facing +x (yaw=0) - i.e.
    #    facing out into the aisle toward the shelves, ready to drive
    #    forward off the charger. z=0.05 gives a small settling drop.
    # -----------------------------------------------------------------
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name", "amr",
            "-topic", "robot_description",
            "-x", "-7.0", "-y", "-5.0", "-z", "0.05",
            "-Y", "0.0",
        ],
        output="screen",
    )

    # -----------------------------------------------------------------
    # 4) ros2_control spawners (delayed until gz_ros2_control has
    #    registered controller_manager after the spawn above).
    # -----------------------------------------------------------------
    spawn_joint_state_broadcaster = TimerAction(
        period=5.0,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=["joint_state_broadcaster"],
            output="screen",
        )],
    )
    spawn_diff_drive_controller = TimerAction(
        period=6.0,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=["diff_drive_controller"],
            output="screen",
        )],
    )

    # -----------------------------------------------------------------
    # 5) Twist -> TwistStamped relay (our own node, in scripts/ -
    #    packages.ros.org was unreachable when we tried the official
    #    twist_stamper package, so this replaces it 1:1). This
    #    installed diff_drive_controller expects TwistStamped on its
    #    cmd_vel topic regardless of use_stamped_vel (confirmed via
    #    `ros2 topic info -v` and the official Jazzy docs) - this lets
    #    you keep using ordinary teleop_twist_keyboard (plain Twist) on
    #    a normal /cmd_vel topic without remembering that quirk.
    # -----------------------------------------------------------------
    twist_stamper = Node(
        package="amr_description",
        executable="twist_to_stamped.py",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    # -----------------------------------------------------------------
    # 6) ros_gz_bridge - Gazebo Transport -> ROS2 topics.
    # -----------------------------------------------------------------
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
            "/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image",
            "/ultrasonic_front_left@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/ultrasonic_front_center@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/ultrasonic_front_right@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        ],
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    return LaunchDescription([
        gazebo,
        robot_state_publisher,
        spawn_robot,
        spawn_joint_state_broadcaster,
        spawn_diff_drive_controller,
        twist_stamper,
        bridge,
    ])
