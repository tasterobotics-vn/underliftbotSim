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

## Installation

### 1. Create the Workspace

```
mkdir -p ~/underliftbot_ws/src 
cd ~/underliftbot_ws/src
```

### 2. Clone the Repository

```
git clone --recurse-submodules https://github.com/tasterobotics-vn/underliftbotSim.git
```

### 3. Run the Setup Script

```
cd ~/underliftbot_ws/src/underliftbotSim 
chmod +x setup.sh ./setup.sh
```

Wait for the setup script to finish installing dependencies and building the workspace.

## Example Run

### 1. Launch the Simulation

Open a terminal and source the ROS 2 environment:

```
source /opt/ros/kilted/setup.bash 
source ~/behavior_tree_ws/install/setup.bash 
source ~/nav2ws/install/setup.bash 
source ~/underliftbot_ws/install/setup.bash
```

Launch the complete simulation:

```
ros2 launch underliftbot_bringup bringup_all.launch.xml
```

**Wait approximately 50 seconds** for the system to initialize before sending a task.

### 2. Send a MoveThings Action Goal

Open a new terminal and source the environments:

```
source ~/underliftbot_ws/install/setup.bash
```

Send an example action goal to move an item from `dock_1A` to `dock_6B`:

```
ros2 action send_goal /move_things custom_message/action/MoveThings '{begin: dock1A, destination: dock_6B}'
```

## Notes

- Several package manifests still have placeholder descriptions/licenses.
- The workspace is heavily simulation-oriented and expects ROS 2, Gazebo, Nav2, AprilTag, and ros2_control packages to be available.
