"""Record AeroLand mission telemetry and perception data to CSV."""

import csv
import math
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from geometry_msgs.msg import Vector3Stamped
from px4_msgs.msg import VehicleLocalPosition
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import Bool, Float32, String


class MissionLogger(Node):
    """Write synchronized mission data to a timestamped CSV file."""

    LOG_PERIOD_SECONDS = 0.1

    def __init__(self):
        super().__init__("aeroland_mission_logger")

        self.declare_parameter(
            "log_directory",
            "~/aeroland_ws/mission_logs",
        )
        directory_value = self.get_parameter(
            "log_directory"
        ).get_parameter_value().string_value
        self.log_directory = Path(directory_value).expanduser()
        self.log_directory.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        self.log_path = self.log_directory / (
            f"aeroland_mission_{timestamp}.csv"
        )
        self.log_file = self.log_path.open(
            "w",
            encoding="utf-8",
            newline="",
        )
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow(
            [
                "elapsed_seconds",
                "mission_state",
                "x_m",
                "y_m",
                "z_ned_m",
                "altitude_m",
                "marker_detected",
                "marker_error_x",
                "marker_error_y",
                "marker_error_norm",
                "landing_confidence",
                "marker_sigma_x_m",
                "marker_sigma_y_m",
                "marker_sigma_radial_m",
                "safe_to_descend",
            ]
        )
        self.log_file.flush()

        self.position = None
        self.mission_state = "UNKNOWN"
        self.marker_detected = False
        self.marker_error_x = 0.0
        self.marker_error_y = 0.0
        self.landing_confidence = 0.0
        self.marker_sigma_x = 0.0
        self.marker_sigma_y = 0.0
        self.marker_sigma_radial = 0.0
        self.safe_to_descend = False
        self.start_time = self.get_clock().now()

        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self._position_callback,
            px4_qos,
        )
        self.create_subscription(
            String,
            "/aeroland/mission/state",
            self._state_callback,
            10,
        )
        self.create_subscription(
            Bool,
            "/aeroland/perception/marker_detected",
            self._marker_callback,
            10,
        )
        self.create_subscription(
            Vector3Stamped,
            "/aeroland/perception/marker_error",
            self._marker_error_callback,
            10,
        )
        self.create_subscription(
            Float32,
            "/aeroland/uncertainty/landing_confidence",
            self._confidence_callback,
            10,
        )
        self.create_subscription(
            Vector3Stamped,
            "/aeroland/uncertainty/marker_sigma",
            self._sigma_callback,
            10,
        )
        self.create_subscription(
            Bool,
            "/aeroland/uncertainty/safe_to_descend",
            self._safe_callback,
            10,
        )
        self.timer = self.create_timer(
            self.LOG_PERIOD_SECONDS,
            self._write_row,
        )

        self.get_logger().info(
            f"Mission logger recording to {self.log_path}"
        )

    def _position_callback(self, message):
        self.position = message

    def _state_callback(self, message):
        self.mission_state = message.data

    def _marker_callback(self, message):
        self.marker_detected = message.data

    def _marker_error_callback(self, message):
        self.marker_error_x = message.vector.x
        self.marker_error_y = message.vector.y

    def _confidence_callback(self, message):
        self.landing_confidence = message.data

    def _sigma_callback(self, message):
        self.marker_sigma_x = message.vector.x
        self.marker_sigma_y = message.vector.y
        self.marker_sigma_radial = message.vector.z

    def _safe_callback(self, message):
        self.safe_to_descend = message.data

    def _elapsed_seconds(self):
        elapsed = self.get_clock().now() - self.start_time
        return elapsed.nanoseconds / 1e9

    def _position_values(self):
        if self.position is None:
            return "", "", "", ""
        return (
            self.position.x,
            self.position.y,
            self.position.z,
            -self.position.z,
        )

    def _marker_values(self):
        if not self.marker_detected:
            return "", "", ""
        error_norm = math.hypot(
            self.marker_error_x,
            self.marker_error_y,
        )
        return (
            self.marker_error_x,
            self.marker_error_y,
            error_norm,
        )

    def _write_row(self):
        x_value, y_value, z_value, altitude = (
            self._position_values()
        )
        error_x, error_y, error_norm = self._marker_values()
        self.csv_writer.writerow(
            [
                f"{self._elapsed_seconds():.3f}",
                self.mission_state,
                x_value,
                y_value,
                z_value,
                altitude,
                int(self.marker_detected),
                error_x,
                error_y,
                error_norm,
                self.landing_confidence,
                self.marker_sigma_x,
                self.marker_sigma_y,
                self.marker_sigma_radial,
                int(self.safe_to_descend),
            ]
        )
        self.log_file.flush()

    def destroy_node(self):
        """Close the CSV file before shutting down the ROS node."""
        if not self.log_file.closed:
            self.log_file.flush()
            self.log_file.close()
        return super().destroy_node()


def main(args=None):
    """Start the AeroLand mission logger."""
    rclpy.init(args=args)
    node = MissionLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
