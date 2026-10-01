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
    confidence_threshold = LaunchConfiguration("confidence_threshold")
    cruise_altitude_m = LaunchConfiguration("cruise_altitude_m")
    log_directory = LaunchConfiguration("log_directory")
    sigma_threshold_m = LaunchConfiguration("sigma_threshold_m")
    start_mission = LaunchConfiguration("start_mission")

    return LaunchDescription(
        [
            SetEnvironmentVariable(
                name="PYTHONNOUSERSITE",
                value="1",
            ),
            DeclareLaunchArgument(
                "confidence_threshold",
                default_value="0.60",
                description="Minimum confidence required for descent.",
            ),
            DeclareLaunchArgument(
                "sigma_threshold_m",
                default_value="0.12",
                description="Maximum radial ground-plane sigma for descent.",
            ),
            DeclareLaunchArgument(
                "cruise_altitude_m",
                default_value="2.50",
                description="Inspection and recovery altitude in meters.",
            ),
            DeclareLaunchArgument(
                "camera_topic",
                default_value=CAMERA_TOPIC,
                description="Gazebo downward-camera image topic.",
            ),
            DeclareLaunchArgument(
                "log_directory",
                default_value="~/aeroland_ws/mission_logs",
                description="Directory for AeroLand mission CSV files.",
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
                package="aeroland_analysis",
                executable="mission_logger",
                name="aeroland_mission_logger",
                parameters=[{"log_directory": log_directory}],
                output="screen",
            ),
            Node(
                package="aeroland_uncertainty",
                executable="landing_confidence",
                name="aeroland_landing_confidence",
                parameters=[
                    {
                        "confidence_limit": confidence_threshold,
                        "sigma_limit_m": sigma_threshold_m,
                    }
                ],
                output="screen",
            ),
            Node(
                package="aeroland_landing",
                executable="inspection_landing",
                name="aeroland_inspection_landing",
                condition=IfCondition(start_mission),
                parameters=[{"cruise_altitude_m": cruise_altitude_m}],
                output="screen",
            ),
        ]
    )
