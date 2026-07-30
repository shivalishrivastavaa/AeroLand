# AeroLand

**Uncertainty-Aware Autonomous Aerial Inspection and Precision Landing Platform**

AeroLand is a simulation-first ROS2 project for developing modular autonomous
robotics software, perception, controls, safety logic, and uncertainty-aware
mission analysis.

The current prototype uses Turtlesim as a controlled environment for learning
and validating ROS2 architecture before transitioning to TurtleBot3, Gazebo,
and a simulated quadrotor.

## Current Capabilities

- Python-based ROS2 nodes using `rclpy`
- Autonomous square-patrol state machine
- Velocity control through `geometry_msgs/Twist`
- Navigation-status communication through ROS2 topics
- Mission Manager that tracks navigation progress
- One-command system startup using a ROS2 launch file
- Clean multi-node shutdown

## Packages

| Package | Responsibility |
|---|---|
| `aeroland_core` | Mission management and system coordination |
| `aeroland_navigation` | Autonomous movement and navigation logic |
| `aeroland_bringup` | System launch configurations |

## Run the Current Demo

```bash
cd ~/aeroland_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch aeroland_bringup turtlesim_patrol.launch.py