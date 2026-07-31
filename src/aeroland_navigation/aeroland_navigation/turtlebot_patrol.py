import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String


class TurtleBotPatrol(Node):
    FORWARD_SPEED = 0.12
    TURN_SPEED = 0.6
    FORWARD_DURATION = 3.0
    TURN_DURATION = (math.pi / 2.0) / TURN_SPEED

    def __init__(self):
        super().__init__("turtlebot_patrol")

        self.velocity_publisher = self.create_publisher(
            Twist,
            "/cmd_vel",
            10,
        )

        self.status_publisher = self.create_publisher(
            String,
            "/aeroland/navigation/status",
            10,
        )

        self.state = "forward"
        self.state_started = self.get_clock().now()
        self.sides_completed = 0

        self.control_timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info("AeroLand TurtleBot3 patrol started")
        self.publish_status("FORWARD")

    def elapsed_in_state(self):
        elapsed = self.get_clock().now() - self.state_started
        return elapsed.nanoseconds / 1e9

    def publish_status(self, status):
        message = String()
        message.data = status
        self.status_publisher.publish(message)
        self.get_logger().info(f"Navigation status: {status}")

    def change_state(self, new_state):
        self.state = new_state
        self.state_started = self.get_clock().now()

        if new_state == "forward":
            self.publish_status("FORWARD")
        elif new_state == "turn":
            self.publish_status("TURNING")

    def control_loop(self):
        command = Twist()
        elapsed = self.elapsed_in_state()

        if self.state == "forward":
            if elapsed < self.FORWARD_DURATION:
                command.linear.x = self.FORWARD_SPEED
            else:
                self.change_state("turn")

        elif self.state == "turn":
            if elapsed < self.TURN_DURATION:
                command.angular.z = self.TURN_SPEED
            else:
                self.sides_completed += 1

                if self.sides_completed % 4 == 0:
                    lap = self.sides_completed // 4
                    self.publish_status(f"LAP_COMPLETE:{lap}")

                self.change_state("forward")

        self.velocity_publisher.publish(command)

    def stop(self):
        self.velocity_publisher.publish(Twist())
        self.publish_status("STOPPED")


def main(args=None):
    rclpy.init(args=args)
    node = TurtleBotPatrol()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.stop()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()