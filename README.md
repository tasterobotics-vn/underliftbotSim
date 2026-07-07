# underliftbotSim

ROS 2 simulation workspace for an underlift mobile robot that can drive under merchandise, lift it, and use docking and AprilTag-based localization support in Gazebo.
<p align="center">
  <img width="400" height="240" alt="underlifting_demo1" src="https://github.com/user-attachments/assets/cc923129-3bc7-46de-bad6-6118dea9605d" />
</p>

## Overview

This repository is organized as a multi-package ROS 2 workspace. The packages split the system into:

- robot description and simulation assets
- low-level controller and Gazebo bridging
- teleoperation
- AprilTag detection and visualization
- Nav2 bringup
- high-level task execution for lift/dock workflows
- custom ROS messages and actions

The repo is centered around a simulated robot that can:

1. Move in Gazebo using velocity commands.
2. Detect AprilTags for docking-related pose estimation.
3. Dock and undock through Nav2 actions.
4. Raise and lower a lift while updating the robot footprint.
5. Execute a higher-level "move things" task via a custom action.

## Package Map

- `underliftbot_description`: URDF/Xacro, robot meshes, Gazebo worlds, bridge config, and the main simulation launch file.
- `underliftbot_controller`: controller launch files plus a small ROS-to-Gazebo command converter.
- `underliftbot_navigation2`: Nav2 bringup wrapper, maps, and Nav2 parameter files.
- `dbot_teleop`: keyboard teleoperation node that publishes `TwistStamped` commands.
- `custom_message`: custom action definitions, especially `MoveThings.action`.
- `apriltag_msgs`: custom AprilTag detection messages used by the detector pipeline.
- `apriltag_ros`: composable AprilTag detector component that publishes detections and TF transforms.
- `apriltag_detection`: AprilTag rectification + detection launch and a node that republishes detected dock poses.
- `apriltag_viz`: composable visualization helper for overlaying detections on camera images.
- `underliftbot_execution`: high-level execution logic that coordinates docking, undocking, and lift motion.

## Runtime Flow

The typical flow in this workspace is:

1. `dbot_teleop` publishes `geometry_msgs/TwistStamped` on `cmd_vel`.
2. `underliftbot_controller/gz_convert` converts that into a plain `Twist` on `cmd_vel_gz` for Gazebo.
3. `underliftbot_description` launches the robot, world, and ROS-Gazebo bridge.
4. `apriltag_ros` detects tags and publishes detections plus TF transforms.
5. `apriltag_detection` turns tag detections into a docking pose stream.
6. `underliftbot_navigation2` brings up Nav2 with the depot map and Nav2 parameters.
7. `underliftbot_execution` coordinates dock, undock, and lift actions through the custom `MoveThings` action.

## Main Launch Entry Points

- `underliftbot_description/launch/underlift_robot_gazebo.launch.xml`
- `underliftbot_controller/launch/controller.launch.py`
- `underliftbot_navigation2/launch/navigation2.launch.py`
- `apriltag_detection/launch/april_detection.launch.py`

## Key Topics And Actions

- `cmd_vel`: teleop velocity input
- `cmd_vel_gz`: Gazebo velocity command
- `cmd_lift_pose`: lift position command
- `/detections`: AprilTag detections
- `detected_dock_pose`: pose published for docking
- `MoveThings`: custom high-level task action

## Notes

- Several package manifests still have placeholder descriptions/licenses.
- The workspace is heavily simulation-oriented and expects ROS 2, Gazebo, Nav2, AprilTag, and ros2_control packages to be available.
