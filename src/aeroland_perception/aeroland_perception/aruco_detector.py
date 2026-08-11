"""Detect the AeroLand ArUco landing marker in ROS camera images."""

import cv2
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import Vector3Stamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from std_msgs.msg import Int32


DEFAULT_CAMERA_TOPIC = (
    "/world/aruco/model/x500_mono_cam_down_0/link/"
    "camera_link/sensor/camera/image"
)


class ArucoDetector(Node):
    """Detect marker zero and publish its normalized image error."""

    def __init__(self):
        """Initialize the AeroLand ArUco detector."""
        super().__init__("aeroland_aruco_detector")

        self.declare_parameter("image_topic", DEFAULT_CAMERA_TOPIC)
        self.declare_parameter("target_marker_id", 0)

        self.image_topic = self.get_parameter("image_topic").value
        self.target_marker_id = self.get_parameter(
            "target_marker_id"
        ).value

        self.bridge = CvBridge()
        self.marker_visible = False

        self.dictionary = cv2.aruco.getPredefinedDictionary(
            cv2.aruco.DICT_4X4_50
        )
        self.detector_parameters = (
            cv2.aruco.DetectorParameters_create()
        )

        self.image_subscription = self.create_subscription(
            Image,
            self.image_topic,
            self.image_callback,
            qos_profile_sensor_data,
        )

        self.annotated_image_publisher = self.create_publisher(
            Image,
            "/aeroland/perception/annotated_image",
            10,
        )
        self.detected_publisher = self.create_publisher(
            Bool,
            "/aeroland/perception/marker_detected",
            10,
        )
        self.marker_id_publisher = self.create_publisher(
            Int32,
            "/aeroland/perception/marker_id",
            10,
        )
        self.marker_error_publisher = self.create_publisher(
            Vector3Stamped,
            "/aeroland/perception/marker_error",
            10,
        )

        self.get_logger().info(
            "AeroLand ArUco detector initialized"
        )
        self.get_logger().info(
            f"Listening for marker {self.target_marker_id} "
            f"on {self.image_topic}"
        )

    def image_callback(self, message):
        """Process one camera image and publish marker information."""
        try:
            frame = self.bridge.imgmsg_to_cv2(
                message,
                desired_encoding="bgr8",
            )
        except CvBridgeError as error:
            self.get_logger().error(
                f"Image conversion failed: {error}"
            )
            return

        annotated_frame = frame.copy()
        gray_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        corners, marker_ids, _ = cv2.aruco.detectMarkers(
            gray_frame,
            self.dictionary,
            parameters=self.detector_parameters,
        )

        height, width = frame.shape[:2]
        image_center = (width // 2, height // 2)

        cv2.drawMarker(
            annotated_frame,
            image_center,
            (255, 0, 0),
            cv2.MARKER_CROSS,
            24,
            2,
        )

        target_indices = []

        if marker_ids is not None:
            cv2.aruco.drawDetectedMarkers(
                annotated_frame,
                corners,
                marker_ids,
            )

            target_indices = [
                index
                for index, marker_id in enumerate(
                    marker_ids.flatten()
                )
                if int(marker_id) == self.target_marker_id
            ]

        marker_detected = bool(target_indices)

        detected_message = Bool()
        detected_message.data = marker_detected
        self.detected_publisher.publish(detected_message)

        if marker_detected:
            marker_index = max(
                target_indices,
                key=lambda index: cv2.contourArea(
                    corners[index].reshape(4, 2)
                ),
            )

            marker_corners = corners[marker_index].reshape(4, 2)
            marker_center = marker_corners.mean(axis=0)

            center_x = int(round(float(marker_center[0])))
            center_y = int(round(float(marker_center[1])))

            horizontal_error = (
                center_x - image_center[0]
            ) / (width / 2.0)
            vertical_error = (
                center_y - image_center[1]
            ) / (height / 2.0)

            marker_area = cv2.contourArea(marker_corners)
            area_fraction = marker_area / float(width * height)

            marker_id_message = Int32()
            marker_id_message.data = self.target_marker_id
            self.marker_id_publisher.publish(marker_id_message)

            error_message = Vector3Stamped()
            error_message.header = message.header
            error_message.vector.x = float(horizontal_error)
            error_message.vector.y = float(vertical_error)
            error_message.vector.z = float(area_fraction)
            self.marker_error_publisher.publish(error_message)

            cv2.circle(
                annotated_frame,
                (center_x, center_y),
                7,
                (0, 0, 255),
                -1,
            )
            cv2.line(
                annotated_frame,
                image_center,
                (center_x, center_y),
                (0, 255, 255),
                2,
            )
            cv2.putText(
                annotated_frame,
                (
                    f"ID {self.target_marker_id} "
                    f"error=({horizontal_error:.3f}, "
                    f"{vertical_error:.3f})"
                ),
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            if not self.marker_visible:
                self.get_logger().info(
                    f"Landing marker acquired: "
                    f"ID {self.target_marker_id}"
                )
        elif self.marker_visible:
            self.get_logger().warning(
                "Landing marker lost"
            )

        self.marker_visible = marker_detected

        annotated_message = self.bridge.cv2_to_imgmsg(
            annotated_frame,
            encoding="bgr8",
        )
        annotated_message.header = message.header
        self.annotated_image_publisher.publish(
            annotated_message
        )


def main(args=None):
    """Run the AeroLand ArUco detector node."""
    rclpy.init(args=args)
    node = ArucoDetector()

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
