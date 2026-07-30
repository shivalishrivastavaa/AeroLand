import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MissionManager(Node):
    def __init__(self):
        super().__init__("mission_manager")

        self.navigation_status = "UNKNOWN"

        self.status_subscription = self.create_subscription(
            String,
            "/aeroland/navigation/status",
            self.navigation_status_callback,
            10,
        )

        self.get_logger().info("AeroLand Mission Manager initialized")
        self.get_logger().info("Waiting for navigation status...")

    def navigation_status_callback(self, message):
        self.navigation_status = message.data
        self.get_logger().info(
            f"Navigation status received: {self.navigation_status}"
        )

        if self.navigation_status.startswith("LAP_COMPLETE:"):
            lap = self.navigation_status.split(":")[1]
            self.get_logger().info(
                f"Mission progress: patrol lap {lap} completed"
            )

        elif self.navigation_status == "STOPPED":
            self.get_logger().warning("Navigation system stopped")


def main(args=None):
    rclpy.init(args=args)
    mission_manager = MissionManager()

    try:
        rclpy.spin(mission_manager)
    except KeyboardInterrupt:
        pass
    finally:
        mission_manager.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()