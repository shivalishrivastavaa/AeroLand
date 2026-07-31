"""Telemetry-aware AeroLand autonomous waypoint mission."""

import math
from dataclasses import dataclass

import rclpy
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


@dataclass(frozen=True)
class Waypoint:
    """A named position in the PX4 local NED coordinate frame."""

    name: str
    x: float
    y: float
    z: float


class WaypointMission(Node):
    """Fly a feedback-driven inspection route and return home."""

    TIMER_PERIOD_SECONDS = 0.1
    PRESTREAM_TICKS = 20
    WAYPOINT_HOLD_TICKS = 10
    WAYPOINT_TIMEOUT_TICKS = 300
    ACTIVATION_TIMEOUT_TICKS = 100
    POSITION_TOLERANCE_METERS = 0.25

    def __init__(self):
        super().__init__("aeroland_waypoint_mission")

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

        self.offboard_mode_publisher = self.create_publisher(
            OffboardControlMode,
            "/fmu/in/offboard_control_mode",
            publisher_qos,
        )

        self.trajectory_publisher = self.create_publisher(
            TrajectorySetpoint,
            "/fmu/in/trajectory_setpoint",
            publisher_qos,
        )

        self.vehicle_command_publisher = self.create_publisher(
            VehicleCommand,
            "/fmu/in/vehicle_command",
            publisher_qos,
        )

        self.position_subscription = self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self.position_callback,
            subscriber_qos,
        )

        self.status_subscription = self.create_subscription(
            VehicleStatus,
            "/fmu/out/vehicle_status_v4",
            self.status_callback,
            subscriber_qos,
        )

        self.waypoints = [
            Waypoint("TAKEOFF", 0.0, 0.0, -2.5),
            Waypoint("INSPECTION_POINT_1", 2.0, 0.0, -2.5),
            Waypoint("INSPECTION_POINT_2", 2.0, 2.0, -2.5),
            Waypoint("INSPECTION_POINT_3", 0.0, 2.0, -2.5),
            Waypoint("RETURN_HOME", 0.0, 0.0, -2.5),
        ]

        self.local_position = None
        self.vehicle_status = None

        self.state = "WAITING_FOR_TELEMETRY"
        self.state_ticks = 0
        self.prestream_ticks = 0
        self.waypoint_index = 0
        self.waypoint_hold_ticks = 0

        self.timer = self.create_timer(
            self.TIMER_PERIOD_SECONDS,
            self.timer_callback,
        )

        self.get_logger().info("AeroLand waypoint mission initialized")
        self.get_logger().info("Waiting for PX4 position and status telemetry...")

    def position_callback(self, message):
        """Store the latest PX4 local position."""
        self.local_position = message

    def status_callback(self, message):
        """Store the latest PX4 vehicle status."""
        self.vehicle_status = message

    def timestamp(self):
        """Return the current ROS time in microseconds."""
        return int(self.get_clock().now().nanoseconds / 1000)

    def telemetry_is_valid(self):
        """Return whether usable position and status data are available."""
        return (
            self.local_position is not None
            and self.vehicle_status is not None
            and self.local_position.xy_valid
            and self.local_position.z_valid
        )

    def vehicle_is_armed(self):
        """Return whether PX4 reports that the vehicle is armed."""
        return (
            self.vehicle_status is not None
            and self.vehicle_status.arming_state
            == VehicleStatus.ARMING_STATE_ARMED
        )

    def vehicle_is_in_offboard(self):
        """Return whether PX4 reports active offboard mode."""
        return (
            self.vehicle_status is not None
            and self.vehicle_status.nav_state
            == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        )

    def publish_offboard_mode(self):
        """Publish the required PX4 offboard heartbeat."""
        message = OffboardControlMode()

        message.timestamp = self.timestamp()
        message.position = True
        message.velocity = False
        message.acceleration = False
        message.attitude = False
        message.body_rate = False
        message.thrust_and_torque = False
        message.direct_actuator = False

        self.offboard_mode_publisher.publish(message)

    def publish_position_setpoint(self, waypoint):
        """Publish one local-NED position target."""
        message = TrajectorySetpoint()
        nan = math.nan

        message.timestamp = self.timestamp()
        message.position = [waypoint.x, waypoint.y, waypoint.z]
        message.velocity = [nan, nan, nan]
        message.acceleration = [nan, nan, nan]
        message.jerk = [nan, nan, nan]
        message.yaw = 0.0
        message.yawspeed = nan

        self.trajectory_publisher.publish(message)

    def publish_vehicle_command(
        self,
        command,
        param1=0.0,
        param2=0.0,
        param3=0.0,
        param4=0.0,
        param5=0.0,
        param6=0.0,
        param7=0.0,
    ):
        """Publish a command to PX4."""
        message = VehicleCommand()

        message.timestamp = self.timestamp()
        message.command = command
        message.param1 = param1
        message.param2 = param2
        message.param3 = param3
        message.param4 = param4
        message.param5 = param5
        message.param6 = param6
        message.param7 = param7
        message.target_system = 1
        message.target_component = 1
        message.source_system = 1
        message.source_component = 1
        message.from_external = True

        self.vehicle_command_publisher.publish(message)

    def request_control(self):
        """Request offboard mode and arm the vehicle."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            param1=1.0,
            param2=6.0,
        )

        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=1.0,
        )

        self.get_logger().info("Offboard and arm commands sent")

    def current_waypoint(self):
        """Return the active mission waypoint."""
        return self.waypoints[self.waypoint_index]

    def distance_to_waypoint(self, waypoint):
        """Calculate three-dimensional distance to a waypoint."""
        dx = self.local_position.x - waypoint.x
        dy = self.local_position.y - waypoint.y
        dz = self.local_position.z - waypoint.z

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def begin_landing(self, reason):
        """Enter landing mode."""
        if self.state == "LANDING":
            return

        self.get_logger().info(f"Landing initiated: {reason}")
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)

        self.state = "LANDING"
        self.state_ticks = 0

    def complete_mission(self):
        """Stop the mission after PX4 confirms disarming."""
        self.state = "COMPLETE"
        self.timer.cancel()

        self.get_logger().info("PX4 confirmed vehicle disarmed")
        self.get_logger().info("AeroLand waypoint mission complete")

    def handle_waiting_for_telemetry(self):
        """Wait until valid PX4 feedback is available."""
        if self.telemetry_is_valid():
            self.state = "PRESTREAM"
            self.state_ticks = 0
            self.get_logger().info("Valid PX4 telemetry received")
            self.get_logger().info("Streaming offboard heartbeat...")
            return

        self.state_ticks += 1

        if self.state_ticks % 50 == 0:
            self.get_logger().info("Still waiting for valid PX4 telemetry...")

    def handle_prestream(self):
        """Stream heartbeat before requesting offboard mode."""
        self.publish_offboard_mode()
        self.prestream_ticks += 1

        if self.prestream_ticks >= self.PRESTREAM_TICKS:
            self.request_control()
            self.state = "ACTIVATING_CONTROL"
            self.state_ticks = 0

    def handle_control_activation(self):
        """Wait for PX4 to confirm arming and offboard mode."""
        self.publish_offboard_mode()

        if self.vehicle_is_in_offboard():
            self.publish_position_setpoint(self.current_waypoint())

        if self.vehicle_is_armed() and self.vehicle_is_in_offboard():
            waypoint = self.current_waypoint()
            self.state = "NAVIGATING"
            self.state_ticks = 0

            self.get_logger().info("PX4 confirmed armed and offboard")
            self.get_logger().info(
                f"Navigating to {waypoint.name}: "
                f"({waypoint.x:.1f}, {waypoint.y:.1f}, {waypoint.z:.1f})"
            )
            return

        self.state_ticks += 1

        if self.state_ticks % 10 == 0:
            self.request_control()

        if self.state_ticks >= self.ACTIVATION_TIMEOUT_TICKS:
            if self.vehicle_is_armed():
                self.begin_landing("control activation timeout")
            else:
                self.get_logger().error(
                    "Control activation failed while vehicle remained disarmed"
                )
                self.state = "COMPLETE"
                self.timer.cancel()

    def handle_navigation(self):
        """Fly toward the active waypoint using telemetry feedback."""
        if not self.vehicle_is_armed():
            self.get_logger().error("Vehicle unexpectedly disarmed")
            self.complete_mission()
            return

        if not self.vehicle_is_in_offboard():
            self.get_logger().error("Offboard mode was lost")
            self.begin_landing("offboard control lost")
            return

        waypoint = self.current_waypoint()

        self.publish_offboard_mode()
        self.publish_position_setpoint(waypoint)

        distance = self.distance_to_waypoint(waypoint)

        if distance <= self.POSITION_TOLERANCE_METERS:
            self.waypoint_hold_ticks += 1
        else:
            self.waypoint_hold_ticks = 0

        if self.waypoint_hold_ticks >= self.WAYPOINT_HOLD_TICKS:
            self.get_logger().info(
                f"Waypoint reached: {waypoint.name} "
                f"(error {distance:.2f} m)"
            )

            if self.waypoint_index == len(self.waypoints) - 1:
                self.begin_landing("inspection route completed")
                return

            self.waypoint_index += 1
            self.waypoint_hold_ticks = 0
            self.state_ticks = 0

            next_waypoint = self.current_waypoint()
            self.get_logger().info(
                f"Navigating to {next_waypoint.name}: "
                f"({next_waypoint.x:.1f}, "
                f"{next_waypoint.y:.1f}, "
                f"{next_waypoint.z:.1f})"
            )
            return

        self.state_ticks += 1

        if self.state_ticks >= self.WAYPOINT_TIMEOUT_TICKS:
            self.get_logger().error(
                f"Waypoint timeout: {waypoint.name}, "
                f"remaining error {distance:.2f} m"
            )
            self.begin_landing("waypoint timeout")

    def handle_landing(self):
        """Repeat the landing request until PX4 disarms."""
        if not self.vehicle_is_armed():
            self.complete_mission()
            return

        if self.state_ticks % 10 == 0:
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)

        self.state_ticks += 1

    def timer_callback(self):
        """Execute one iteration of the mission state machine."""
        if self.state == "WAITING_FOR_TELEMETRY":
            self.handle_waiting_for_telemetry()
        elif self.state == "PRESTREAM":
            self.handle_prestream()
        elif self.state == "ACTIVATING_CONTROL":
            self.handle_control_activation()
        elif self.state == "NAVIGATING":
            self.handle_navigation()
        elif self.state == "LANDING":
            self.handle_landing()


def main(args=None):
    """Start the AeroLand waypoint mission."""
    rclpy.init(args=args)
    node = WaypointMission()

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
