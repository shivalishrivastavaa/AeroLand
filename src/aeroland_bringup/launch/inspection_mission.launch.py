"""Launch the AeroLand integrated inspection and landing stack."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


CAMERA_TOPIC = (
    "/world/aruco/model/x500_mono_cam_down_0/link/camera_link/"
    "sensor/camera/image"
)


def generate_launch_description():
    """Create the AeroLand integrated mission launch description."""
    camera_topic = LaunchConfiguration("camera_topic")
    start_mission = LaunchConfiguration("start_mission")

    return LaunchDescription(
        [
            SetEnvironmentVariable(
                name="PYTHONNOUSERSITE",
                value="1",
            ),
            DeclareLaunchArgument(
                "camera_topic",
                default_value=CAMERA_TOPIC,
                description="Gazebo downward-camera image topic.",
            ),
            DeclareLaunchArgument(
                "start_mission",
                default_value="false",
                description="Start autonomous flight when true.",
            ),
            Node(
                package="ros_gz_image",
                executable="image_bridge",
                name="aeroland_camera_bridge",
                arguments=[camera_topic],
                output="screen",
            ),
            Node(
                package="aeroland_perception",
                executable="aruco_detector",
                name="aeroland_aruco_detector",
                remappings=[(CAMERA_TOPIC, camera_topic)],
                output="screen",
            ),
            Node(
                package="aeroland_landing",
                executable="inspection_landing",
                name="aeroland_inspection_landing",
                condition=IfCondition(start_mission),
                output="screen",
            ),
        ]
    )
