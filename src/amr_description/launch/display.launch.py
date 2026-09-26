#!/usr/bin/env python3
"""
display.launch.py
==================
Sanity-check the URDF and TF tree WITHOUT Gazebo. Always run this first
after editing the xacro files - much faster to spot a broken joint here
(via joint_state_publisher_gui sliders + RViz) than after waiting for
Gazebo to boot.

Run with:
    ros2 launch amr_description display.launch.py
"""

import os
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory("amr_description")
    xacro_file = os.path.join(pkg_share, "urdf", "amr.urdf.xacro")

    # Run the xacro file through `xacro` at launch time, feed the
    # resulting URDF/XML string to robot_state_publisher.
    robot_description = ParameterValue(
        Command(["xacro ", xacro_file]), value_type=str
    )

    return LaunchDescription([
        # Publishes /tf (base_footprint -> base_link -> ...) computed
        # from the URDF + current joint states.
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description,
                         "use_sim_time": False}],
        ),

        # Fakes joint_states with GUI sliders (no real hardware/Gazebo
        # here) - lets you manually spin all four wheels and watch TF.
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            output="screen",
        ),

        Node(
            package="rviz2",
            executable="rviz2",
            output="screen",
        ),
    ])