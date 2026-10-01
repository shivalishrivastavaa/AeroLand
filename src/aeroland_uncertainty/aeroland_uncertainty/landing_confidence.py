"""Estimate uncertainty and landing confidence for AeroLand."""

import math
from collections import deque

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


class LandingConfidenceEstimator(Node):
    """Estimate whether visual guidance is reliable enough to descend."""

    PERIOD = 0.1
    SAMPLE_WINDOW = 20
    MIN_SAMPLES = 8
    FRESH_TIMEOUT = 0.6

    HORIZONTAL_FOV = 1.74
    IMAGE_WIDTH = 640.0
    IMAGE_HEIGHT = 480.0

    CENTER_LIMIT = 0.10
    SIGMA_LIMIT_METERS = 0.12
    AVAILABILITY_LIMIT = 0.75
    CONFIDENCE_LIMIT = 0.60

    CENTER_CONFIDENCE_SCALE = 0.12
    SIGMA_CONFIDENCE_SCALE_METERS = 0.12

    GUIDANCE_STATES = {"SEARCH", "ALIGN", "DESCEND", "RECOVER"}
    DESCENT_STATES = {"ALIGN", "DESCEND"}

    def __init__(self):
        super().__init__("aeroland_landing_confidence")

        self.declare_parameter("confidence_limit", self.CONFIDENCE_LIMIT)
        self.declare_parameter("sigma_limit_m", self.SIGMA_LIMIT_METERS)
        self.CONFIDENCE_LIMIT = float(
            self.get_parameter("confidence_limit").value
        )
        self.SIGMA_LIMIT_METERS = float(
            self.get_parameter("sigma_limit_m").value
        )

        px4_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self.confidence_publisher = self.create_publisher(
            Float32,
            "/aeroland/uncertainty/landing_confidence",
            10,
        )
        self.sigma_publisher = self.create_publisher(
            Vector3Stamped,
            "/aeroland/uncertainty/marker_sigma",
            10,
        )
        self.safe_publisher = self.create_publisher(
            Bool,
            "/aeroland/uncertainty/safe_to_descend",
            10,
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

        self.position = None
        self.mission_state = "UNKNOWN"
        self.marker_detected = False
        self.last_error_time = None
        self.error_samples = deque(maxlen=self.SAMPLE_WINDOW)
        self.detection_samples = deque(maxlen=self.SAMPLE_WINDOW)
        self.last_safe = None
        self.timer_ticks = 0

        self.timer = self.create_timer(self.PERIOD, self._timer_callback)
        self.get_logger().info(
            "AeroLand landing-confidence estimator initialized "
            f"(confidence >= {self.CONFIDENCE_LIMIT:.2f}, "
            f"sigma <= {self.SIGMA_LIMIT_METERS:.3f} m)"
        )

    def _position_callback(self, message):
        self.position = message

    def _state_callback(self, message):
        previous_state = self.mission_state
        self.mission_state = message.data
        if (
            self.mission_state in {"SEARCH", "RECOVER"}
            and self.mission_state != previous_state
        ):
            self._reset_window()

    def _marker_callback(self, message):
        self.marker_detected = message.data
        self.detection_samples.append(bool(message.data))
        if not message.data:
            self.error_samples.clear()
            self.last_error_time = None

    def _marker_error_callback(self, message):
        self.marker_detected = True
        self.last_error_time = self.get_clock().now()
        self.error_samples.append(
            (float(message.vector.x), float(message.vector.y))
        )

    def _reset_window(self):
        self.error_samples.clear()
        self.detection_samples.clear()
        self.last_error_time = None

    def _telemetry_valid(self):
        return (
            self.position is not None
            and self.position.z_valid
            and math.isfinite(self.position.z)
        )

    def _marker_fresh(self):
        if not self.marker_detected or self.last_error_time is None:
            return False
        age = (
            self.get_clock().now() - self.last_error_time
        ).nanoseconds / 1e9
        return age <= self.FRESH_TIMEOUT

    @staticmethod
    def _mean(values):
        return sum(values) / len(values)

    @classmethod
    def _sample_standard_deviation(cls, values):
        if len(values) < 2:
            return 0.0
        mean_value = cls._mean(values)
        variance = sum(
            (value - mean_value) ** 2 for value in values
        ) / (len(values) - 1)
        return math.sqrt(max(variance, 0.0))

    def _vertical_fov(self):
        half_horizontal = math.tan(self.HORIZONTAL_FOV / 2.0)
        half_vertical = (
            half_horizontal * self.IMAGE_HEIGHT / self.IMAGE_WIDTH
        )
        return 2.0 * math.atan(half_vertical)

    def _ground_scales(self):
        altitude = max(-float(self.position.z), 0.0)
        x_scale = altitude * math.tan(self.HORIZONTAL_FOV / 2.0)
        y_scale = altitude * math.tan(self._vertical_fov() / 2.0)
        return x_scale, y_scale

    def _detection_availability(self):
        if not self.detection_samples:
            return 0.0
        detected_count = sum(
            1 for detected in self.detection_samples if detected
        )
        return detected_count / len(self.detection_samples)

    def _calculate_estimate(self):
        estimate = {
            "confidence": 0.0,
            "sigma_x": 0.0,
            "sigma_y": 0.0,
            "sigma_radial": 0.0,
            "center_error": float("inf"),
            "availability": self._detection_availability(),
            "safe": False,
        }
        if (
            not self._telemetry_valid()
            or not self._marker_fresh()
            or len(self.error_samples) < self.MIN_SAMPLES
        ):
            return estimate

        error_x_values = [sample[0] for sample in self.error_samples]
        error_y_values = [sample[1] for sample in self.error_samples]
        mean_x = self._mean(error_x_values)
        mean_y = self._mean(error_y_values)
        sigma_x_normalized = self._sample_standard_deviation(
            error_x_values
        )
        sigma_y_normalized = self._sample_standard_deviation(
            error_y_values
        )

        x_scale, y_scale = self._ground_scales()
        sigma_x = abs(x_scale * sigma_x_normalized)
        sigma_y = abs(y_scale * sigma_y_normalized)
        sigma_radial = math.hypot(sigma_x, sigma_y)
        center_error = math.hypot(mean_x, mean_y)
        availability = self._detection_availability()

        center_quality = math.exp(
            -0.5
            * (center_error / self.CENTER_CONFIDENCE_SCALE) ** 2
        )
        sigma_quality = math.exp(
            -0.5
            * (
                sigma_radial
                / self.SIGMA_CONFIDENCE_SCALE_METERS
            )
            ** 2
        )
        confidence = max(
            0.0,
            min(1.0, availability * center_quality * sigma_quality),
        )
        safe = (
            self.mission_state in self.DESCENT_STATES
            and center_error <= self.CENTER_LIMIT
            and sigma_radial <= self.SIGMA_LIMIT_METERS
            and availability >= self.AVAILABILITY_LIMIT
            and confidence >= self.CONFIDENCE_LIMIT
        )

        estimate.update(
            {
                "confidence": confidence,
                "sigma_x": sigma_x,
                "sigma_y": sigma_y,
                "sigma_radial": sigma_radial,
                "center_error": center_error,
                "availability": availability,
                "safe": safe,
            }
        )
        return estimate

    def _publish_estimate(self, estimate):
        confidence_message = Float32()
        confidence_message.data = float(estimate["confidence"])
        self.confidence_publisher.publish(confidence_message)

        sigma_message = Vector3Stamped()
        sigma_message.header.stamp = self.get_clock().now().to_msg()
        sigma_message.header.frame_id = "camera_ground_plane"
        sigma_message.vector.x = float(estimate["sigma_x"])
        sigma_message.vector.y = float(estimate["sigma_y"])
        sigma_message.vector.z = float(estimate["sigma_radial"])
        self.sigma_publisher.publish(sigma_message)

        safe_message = Bool()
        safe_message.data = bool(estimate["safe"])
        self.safe_publisher.publish(safe_message)

    def _log_transition(self, estimate):
        safe = bool(estimate["safe"])
        if self.last_safe is None:
            self.last_safe = safe
            return
        if safe == self.last_safe:
            return
        self.last_safe = safe
        if safe:
            self.get_logger().info(
                "Visual uncertainty accepted; descent is safe "
                f"(confidence {estimate['confidence']:.2f}, "
                f"sigma {estimate['sigma_radial']:.3f} m)"
            )
        else:
            self.get_logger().warning(
                "Visual uncertainty rejected; descent paused "
                f"(confidence {estimate['confidence']:.2f})"
            )

    def _log_status(self, estimate):
        if self.mission_state not in self.GUIDANCE_STATES:
            return
        if self.timer_ticks % 10 != 0:
            return
        self.get_logger().info(
            "Landing confidence: "
            f"score={estimate['confidence']:.2f}, "
            f"sigma={estimate['sigma_radial']:.3f} m, "
            f"center={estimate['center_error']:.3f}, "
            f"availability={estimate['availability']:.2f}, "
            f"safe={estimate['safe']}"
        )

    def _timer_callback(self):
        estimate = self._calculate_estimate()
        self._publish_estimate(estimate)
        self._log_transition(estimate)
        self._log_status(estimate)
        self.timer_ticks += 1


def main(args=None):
    """Start the AeroLand landing-confidence estimator."""
    rclpy.init(args=args)
    node = LandingConfidenceEstimator()
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
