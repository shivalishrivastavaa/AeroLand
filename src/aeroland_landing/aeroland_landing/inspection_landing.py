"""Integrated AeroLand inspection and precision-landing mission."""

import math
from dataclasses import dataclass

import rclpy

from aeroland_landing.precision_landing import PrecisionLanding


@dataclass(frozen=True)
class InspectionWaypoint:
    """A named inspection position relative to the takeoff location."""

    name: str
    north: float
    east: float


class InspectionLandingMission(PrecisionLanding):
    """Fly an inspection route before performing precision landing."""

    INSPECTION_TOLERANCE = 0.25
    INSPECTION_HOLD_TICKS = 10
    INSPECTION_TIMEOUT = 300

    def __init__(self):
        super().__init__()

        self.inspection_waypoints = [
            InspectionWaypoint("INSPECTION_POINT_1", 2.0, 0.0),
            InspectionWaypoint("INSPECTION_POINT_2", 2.0, 2.0),
            InspectionWaypoint("INSPECTION_POINT_3", 0.0, 2.0),
            InspectionWaypoint("RETURN_HOME", 0.0, 0.0),
        ]
        self.inspection_index = 0

        self.get_logger().info(
            "Integrated inspection and precision-landing mission ready"
        )

    def _current_inspection_waypoint(self):
        """Return the active inspection waypoint."""
        return self.inspection_waypoints[self.inspection_index]

    def _set_inspection_target(self, waypoint):
        """Set the local-NED target for an inspection waypoint."""
        self.target_x = self.home_x + waypoint.north
        self.target_y = self.home_y + waypoint.east
        self.target_z = self.TAKEOFF_Z

    def _distance_to_inspection_target(self):
        """Return three-dimensional distance to the current target."""
        north_error = self.position.x - self.target_x
        east_error = self.position.y - self.target_y
        altitude_error = self.position.z - self.target_z

        return math.sqrt(
            north_error * north_error
            + east_error * east_error
            + altitude_error * altitude_error
        )

    def _handle_takeoff(self):
        """Take off, then transition into the inspection route."""
        if not self._flight_safe():
            return

        self._publish_control()

        if abs(self.position.z - self.TAKEOFF_Z) <= self.TAKEOFF_TOLERANCE:
            self.stable_ticks += 1
        else:
            self.stable_ticks = 0

        if self.stable_ticks >= self.TAKEOFF_HOLD_TICKS:
            waypoint = self._current_inspection_waypoint()
            self._set_inspection_target(waypoint)
            self._enter(
                "INSPECTION",
                f"Takeoff complete; navigating to {waypoint.name}",
            )
            return

        self.state_ticks += 1

        if self.state_ticks >= self.TAKEOFF_TIMEOUT:
            self._begin_landing("takeoff timeout")

    def _handle_inspection(self):
        """Navigate through the inspection route using PX4 feedback."""
        if not self._flight_safe():
            return

        waypoint = self._current_inspection_waypoint()
        self._set_inspection_target(waypoint)
        self._publish_control()

        distance = self._distance_to_inspection_target()

        if distance <= self.INSPECTION_TOLERANCE:
            self.stable_ticks += 1
        else:
            self.stable_ticks = 0

        if self.stable_ticks >= self.INSPECTION_HOLD_TICKS:
            self.get_logger().info(
                f"Waypoint reached: {waypoint.name} "
                f"(error {distance:.2f} m)"
            )

            if self.inspection_index == len(self.inspection_waypoints) - 1:
                self.target_x = self.home_x
                self.target_y = self.home_y
                self.target_z = self.TAKEOFF_Z
                self._enter(
                    "SEARCH",
                    "Inspection route complete; searching for marker",
                )
                return

            self.inspection_index += 1
            next_waypoint = self._current_inspection_waypoint()
            self._set_inspection_target(next_waypoint)
            self._enter(
                "INSPECTION",
                f"Navigating to {next_waypoint.name}",
            )
            return

        self.state_ticks += 1

        if self.state_ticks >= self.INSPECTION_TIMEOUT:
            self.get_logger().error(
                f"Inspection waypoint timeout: {waypoint.name}"
            )
            self._begin_landing("inspection waypoint timeout")

    def _timer_callback(self):
        """Execute one iteration of the integrated mission."""
        handlers = {
            "WAITING": self._handle_waiting,
            "PRESTREAM": self._handle_prestream,
            "ACTIVATE": self._handle_activate,
            "TAKEOFF": self._handle_takeoff,
            "INSPECTION": self._handle_inspection,
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
    """Start the integrated inspection and landing mission."""
    rclpy.init(args=args)
    node = InspectionLandingMission()

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
