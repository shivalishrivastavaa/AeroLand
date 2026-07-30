from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="turtlesim",
                executable="turtlesim_node",
                name="turtlesim",
                output="screen",
            ),
            Node(
                package="aeroland_core",
                executable="mission_manager",
                name="mission_manager",
                output="screen",
            ),
            Node(
                package="aeroland_navigation",
                executable="turtle_patrol",
                name="turtle_patrol",
                output="screen",
            ),
        ]
    )