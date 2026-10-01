"""Provide the MAVLink GCS heartbeat required by PX4 SITL arming checks."""

from __future__ import annotations

import os
import time

from pymavlink import mavutil


def main() -> None:
    """Wait for PX4, then identify AeroLand as a local ground station."""
    port = int(os.getenv("AEROLAND_GCS_PORT", "14550"))
    connection = mavutil.mavlink_connection(
        f"udpin:0.0.0.0:{port}",
        source_system=255,
        source_component=190,
    )

    print(f"Waiting for PX4 MAVLink traffic on UDP {port}...", flush=True)
    connection.wait_heartbeat()
    print("PX4 detected; AeroLand GCS heartbeat active", flush=True)

    while True:
        connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0,
            0,
            mavutil.mavlink.MAV_STATE_ACTIVE,
        )
        time.sleep(1.0)


if __name__ == "__main__":
    main()
