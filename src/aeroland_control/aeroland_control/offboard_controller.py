"""AeroLand PX4 offboard takeoff, hover, and landing controller."""

import math

import rclpy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)


class OffboardController(Node):
    """Control the simulated X500 through a basic autonomous flight."""

    TIMER_PERIOD_SECONDS = 0.1
    PRESTREAM_TICKS = 20
    FLIGHT_TICKS = 150
    TAKEOFF_ALTITUDE_METERS = -2.5  # Negative means upward in PX4's NED frame.

    def __init__(self):
        super().__init__("aeroland_offboard_controller")

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.offboard_mode_publisher = self.create_publisher(
            OffboardControlMode,
            "/fmu/in/offboard_control_mode",
            qos_profile,
        )

        self.trajectory_publisher = self.create_publisher(
            TrajectorySetpoint,
            "/fmu/in/trajectory_setpoint",
            qos_profile,
        )

        self.vehicle_command_publisher = self.create_publisher(
            VehicleCommand,
            "/fmu/in/vehicle_command",
            qos_profile,
        )

        self.tick_count = 0
        self.landing_started = False

        self.timer = self.create_timer(
            self.TIMER_PERIOD_SECONDS,
            self.timer_callback,
        )

        self.get_logger().info("AeroLand offboard controller initialized")
        self.get_logger().info("Streaming safety setpoints before takeoff...")

    def timestamp(self):
        """Return the current ROS time in microseconds."""
        return int(self.get_clock().now().nanoseconds / 1000)

    def publish_offboard_mode(self):
        """Publish the PX4 offboard-control heartbeat."""
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

    def publish_position_setpoint(self):
        """Command the drone to hold above its starting position."""
        message = TrajectorySetpoint()

        message.timestamp = self.timestamp()
        message.position = [
            0.0,
            0.0,
            self.TAKEOFF_ALTITUDE_METERS,
        ]

        nan = math.nan
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
        """Send a command to PX4."""
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

    def enter_offboard_mode(self):
        """Request PX4 offboard mode."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            param1=1.0,
            param2=6.0,
        )
        self.get_logger().info("Offboard-mode command sent")

    def arm(self):
        """Arm the simulated drone."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=1.0,
        )
        self.get_logger().info("Arm command sent")

    def land(self):
        """Tell PX4 to land at the current location."""
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_NAV_LAND,
        )
        self.get_logger().info("Landing command sent")
        self.get_logger().info("AeroLand demonstration mission complete")

    def timer_callback(self):
        """Run the autonomous flight sequence at 10 Hz."""
        if self.landing_started:
            return

        self.publish_offboard_mode()
        self.publish_position_setpoint()

        if self.tick_count == self.PRESTREAM_TICKS:
            self.enter_offboard_mode()
            self.arm()
            self.get_logger().info(
                "Takeoff started: target altitude is 2.5 meters"
            )

        landing_tick = self.PRESTREAM_TICKS + self.FLIGHT_TICKS

        if self.tick_count == landing_tick:
            self.land()
            self.landing_started = True

        self.tick_count += 1


def main(args=None):
    """Start the AeroLand offboard controller."""
    rclpy.init(args=args)
    node = OffboardController()

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