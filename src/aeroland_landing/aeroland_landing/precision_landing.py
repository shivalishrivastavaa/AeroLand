"""Vision-guided precision landing controller for AeroLand."""

import math

import rclpy
from geometry_msgs.msg import Vector3Stamped
from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleLocalPosition,
    VehicleStatus,
)
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import Bool


class PrecisionLanding(Node):
    """Center an X500 over an ArUco marker and land safely."""

    PERIOD = 0.1
    PRESTREAM_TICKS = 20
    ACTIVATION_TIMEOUT = 100
    TAKEOFF_Z = -2.5
    TAKEOFF_TOLERANCE = 0.25
    TAKEOFF_HOLD_TICKS = 10
    TAKEOFF_TIMEOUT = 300
    MARKER_TIMEOUT = 1.2
    ACQUIRE_TICKS = 5
    SEARCH_TIMEOUT = 300
    ALIGN_TOLERANCE = 0.08
    ALIGN_HOLD_TICKS = 10
    REALIGN_THRESHOLD = 0.20
    HORIZONTAL_GAIN = 0.7
    MAX_CORRECTION = 0.18
    MAX_HOME_OFFSET = 2.0
    DESCENT_STEP = 0.025
    FINAL_LAND_Z = -1.00
    DESCENT_TIMEOUT = 800
    RECOVERY_TIMEOUT = 300

    def __init__(self):
        super().__init__("aeroland_precision_landing")

        publisher_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        subscriber_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self.offboard_publisher = self.create_publisher(
            OffboardControlMode,
            "/fmu/in/offboard_control_mode",
            publisher_qos,
        )
        self.setpoint_publisher = self.create_publisher(
            TrajectorySetpoint,
            "/fmu/in/trajectory_setpoint",
            publisher_qos,
        )
        self.command_publisher = self.create_publisher(
            VehicleCommand,
            "/fmu/in/vehicle_command",
            publisher_qos,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self._position_callback,
            subscriber_qos,
        )
        self.create_subscription(
            VehicleStatus,
            "/fmu/out/vehicle_status_v4",
            self._status_callback,
            subscriber_qos,
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
        self.status = None
        self.marker_detected = False
        self.marker_error_x = 0.0
        self.marker_error_y = 0.0
        self.last_marker_time = None

        self.home_x = 0.0
        self.home_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = self.TAKEOFF_Z

        self.state = "WAITING"
        self.state_ticks = 0
        self.prestream_ticks = 0
        self.stable_ticks = 0
        self.timer = self.create_timer(self.PERIOD, self._timer_callback)

        self.get_logger().info("AeroLand precision landing initialized")
        self.get_logger().info("Waiting for PX4 telemetry and perception...")

    def _position_callback(self, message):
        self.position = message

    def _status_callback(self, message):
        self.status = message

    def _marker_callback(self, message):
        self.marker_detected = message.data
        if message.data:
            self.last_marker_time = self.get_clock().now()

    def _marker_error_callback(self, message):
        self.marker_error_x = message.vector.x
        self.marker_error_y = message.vector.y
        self.marker_detected = True
        self.last_marker_time = self.get_clock().now()

    def _timestamp(self):
        return int(self.get_clock().now().nanoseconds / 1000)

    def _telemetry_valid(self):
        return (
            self.position is not None
            and self.status is not None
            and self.position.xy_valid
            and self.position.z_valid
        )

    def _armed(self):
        return (
            self.status is not None
            and self.status.arming_state
            == VehicleStatus.ARMING_STATE_ARMED
        )

    def _offboard(self):
        return (
            self.status is not None
            and self.status.nav_state
            == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        )

    def _marker_fresh(self):
        if self.last_marker_time is None:
            return False
        age = (
            self.get_clock().now() - self.last_marker_time
        ).nanoseconds / 1e9
        return age <= self.MARKER_TIMEOUT

    def _publish_offboard(self):
        message = OffboardControlMode()
        message.timestamp = self._timestamp()
        message.position = True
        message.velocity = False
        message.acceleration = False
        message.attitude = False
        message.body_rate = False
        message.thrust_and_torque = False
        message.direct_actuator = False
        self.offboard_publisher.publish(message)

    def _publish_setpoint(self):
        message = TrajectorySetpoint()
        nan = math.nan
        message.timestamp = self._timestamp()
        message.position = [
            float(self.target_x),
            float(self.target_y),
            float(self.target_z),
        ]
        message.velocity = [nan, nan, nan]
        message.acceleration = [nan, nan, nan]
        message.jerk = [nan, nan, nan]
        message.yaw = 0.0
        message.yawspeed = nan
        self.setpoint_publisher.publish(message)

    def _publish_command(self, command, param1=0.0, param2=0.0):
        message = VehicleCommand()
        message.timestamp = self._timestamp()
        message.command = command
        message.param1 = param1
        message.param2 = param2
        message.target_system = 1
        message.target_component = 1
        message.source_system = 1
        message.source_component = 1
        message.from_external = True
        self.command_publisher.publish(message)

    def _publish_control(self):
        self._publish_offboard()
        self._publish_setpoint()

    def _request_control(self):
        self._publish_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            param1=1.0,
            param2=6.0,
        )
        self._publish_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=1.0,
        )
        self.get_logger().info("Offboard and arm commands sent")

    def _enter(self, state, message):
        self.state = state
        self.state_ticks = 0
        self.stable_ticks = 0
        self.get_logger().info(message)

    def _begin_landing(self, reason):
        if self.state == "LANDING":
            return
        self._publish_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self._enter("LANDING", f"Final landing initiated: {reason}")

    def _complete(self):
        self.state = "COMPLETE"
        self.timer.cancel()
        self.get_logger().info("PX4 confirmed vehicle disarmed")
        self.get_logger().info("AeroLand precision landing complete")

    def _flight_safe(self):
        if not self._armed():
            self.get_logger().error("Vehicle unexpectedly disarmed")
            self._complete()
            return False
        if not self._offboard():
            self.get_logger().error("Offboard mode was lost")
            self._begin_landing("offboard control lost")
            return False
        return True

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(value, maximum))

    def _image_error(self):
        return max(abs(self.marker_error_x), abs(self.marker_error_y))

    def _update_horizontal_target(self):
        # Down-camera image axes map to local NED axes with negative signs.
        north = self._clamp(
            -self.HORIZONTAL_GAIN * self.marker_error_y,
            -self.MAX_CORRECTION,
            self.MAX_CORRECTION,
        )
        east = self._clamp(
            self.HORIZONTAL_GAIN * self.marker_error_x,
            -self.MAX_CORRECTION,
            self.MAX_CORRECTION,
        )
        self.target_x = self._clamp(
            self.position.x + north,
            self.home_x - self.MAX_HOME_OFFSET,
            self.home_x + self.MAX_HOME_OFFSET,
        )
        self.target_y = self._clamp(
            self.position.y + east,
            self.home_y - self.MAX_HOME_OFFSET,
            self.home_y + self.MAX_HOME_OFFSET,
        )

    def _handle_waiting(self):
        if self._telemetry_valid():
            self.home_x = self.position.x
            self.home_y = self.position.y
            self.target_x = self.home_x
            self.target_y = self.home_y
            self.target_z = self.TAKEOFF_Z
            self._enter("PRESTREAM", "Valid PX4 telemetry received")
            return
        self.state_ticks += 1
        if self.state_ticks % 50 == 0:
            self.get_logger().info("Still waiting for PX4 telemetry...")

    def _handle_prestream(self):
        self._publish_control()
        self.prestream_ticks += 1
        if self.prestream_ticks >= self.PRESTREAM_TICKS:
            self._request_control()
            self._enter("ACTIVATE", "Waiting for armed offboard mode...")

    def _handle_activate(self):
        self._publish_control()
        if self._armed() and self._offboard():
            self._enter("TAKEOFF", "Taking off to 2.5 meters")
            return
        self.state_ticks += 1
        if self.state_ticks % 10 == 0:
            self._request_control()
        if self.state_ticks >= self.ACTIVATION_TIMEOUT:
            if self._armed():
                self._begin_landing("control activation timeout")
            else:
                self.get_logger().error("Control activation failed")
                self.timer.cancel()

    def _handle_takeoff(self):
        if not self._flight_safe():
            return
        self._publish_control()
        if abs(self.position.z - self.TAKEOFF_Z) <= self.TAKEOFF_TOLERANCE:
            self.stable_ticks += 1
        else:
            self.stable_ticks = 0
        if self.stable_ticks >= self.TAKEOFF_HOLD_TICKS:
            self._enter("SEARCH", "Takeoff complete; searching for marker")
            return
        self.state_ticks += 1
        if self.state_ticks >= self.TAKEOFF_TIMEOUT:
            self._begin_landing("takeoff timeout")

    def _handle_search(self):
        if not self._flight_safe():
            return
        self._publish_control()
        if self._marker_fresh():
            self.stable_ticks += 1
        else:
            self.stable_ticks = 0
        if self.stable_ticks >= self.ACQUIRE_TICKS:
            self._enter("ALIGN", "Marker acquired; beginning alignment")
            return
        self.state_ticks += 1
        if self.state_ticks >= self.SEARCH_TIMEOUT:
            self._begin_landing("marker search timeout")

    def _handle_align(self):
        if not self._flight_safe():
            return
        if not self._marker_fresh():
            self._start_recovery("marker lost during alignment")
            return
        self._update_horizontal_target()
        self.target_z = self.TAKEOFF_Z
        self._publish_control()
        error = self._image_error()
        if self.state_ticks % 10 == 0:
            self.get_logger().info(
                "Alignment telemetry: "
                f"error=({self.marker_error_x:.3f}, "
                f"{self.marker_error_y:.3f}), "
                f"position=({self.position.x:.2f}, "
                f"{self.position.y:.2f}), "
                f"target=({self.target_x:.2f}, "
                f"{self.target_y:.2f})"
            )
        self.state_ticks += 1
        if error <= self.ALIGN_TOLERANCE:
            self.stable_ticks += 1
        else:
            self.stable_ticks = 0
        if self.stable_ticks >= self.ALIGN_HOLD_TICKS:
            self.target_z = self.position.z
            self._enter(
                "DESCEND",
                f"Marker centered; descending (error {error:.3f})",
            )

    def _handle_descend(self):
        if not self._flight_safe():
            return
        if not self._marker_fresh():
            self._start_recovery("marker lost during descent")
            return
        if not self.marker_detected:
            self.target_z = self.position.z
            self._publish_control()
            self.state_ticks += 1
            return
        error = self._image_error()
        self._update_horizontal_target()
        if error > self.REALIGN_THRESHOLD:
            self.target_z = self.position.z
            self._enter(
                "ALIGN",
                f"Descent paused for realignment (error {error:.3f})",
            )
            return
        self.target_z = min(
            self.target_z + self.DESCENT_STEP,
            self.FINAL_LAND_Z,
        )
        self._publish_control()
        if self.state_ticks % 10 == 0:
            self.get_logger().info(
                "Descent telemetry: "
                f"altitude={-self.position.z:.2f} m, "
                f"error=({self.marker_error_x:.3f}, "
                f"{self.marker_error_y:.3f})"
            )
        if self.position.z >= self.FINAL_LAND_Z:
            self._begin_landing("precision descent completed")
            return
        self.state_ticks += 1
        if self.state_ticks >= self.DESCENT_TIMEOUT:
            self._start_recovery("descent timeout")

    def _start_recovery(self, reason):
        self.target_x = self.home_x
        self.target_y = self.home_y
        self.target_z = self.TAKEOFF_Z
        self._enter("RECOVER", f"Recovery initiated: {reason}")

    def _handle_recover(self):
        if not self._flight_safe():
            return
        self._publish_control()
        if abs(self.position.z - self.TAKEOFF_Z) <= self.TAKEOFF_TOLERANCE:
            self._enter("SEARCH", "Recovery complete; searching again")
            return
        self.state_ticks += 1
        if self.state_ticks >= self.RECOVERY_TIMEOUT:
            self._begin_landing("recovery timeout")

    def _handle_landing(self):
        if not self._armed():
            self._complete()
            return
        if self.state_ticks % 10 == 0:
            self._publish_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.state_ticks += 1

    def _timer_callback(self):
        handlers = {
            "WAITING": self._handle_waiting,
            "PRESTREAM": self._handle_prestream,
            "ACTIVATE": self._handle_activate,
            "TAKEOFF": self._handle_takeoff,
            "SEARCH": self._handle_search,
            "ALIGN": self._handle_align,
            "DESCEND": self._handle_descend,
            "RECOVER": self._handle_recover,
            "LANDING": self._handle_landing,
        }
        handler = handlers.get(self.state)
        if handler is not None:
            handler()


def main(args=None):
    """Start the AeroLand precision-landing controller."""
    rclpy.init(args=args)
    node = PrecisionLanding()
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
