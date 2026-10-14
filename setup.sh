#!/usr/bin/env bash

set -e

# ============================================================
# Configuration
# ============================================================

ROS_DISTRO="${ROS_DISTRO:-kilted}"
JOBS=8

BT_WS="$HOME/behavior_tree_ws"
NAV2_WS="$HOME/nav2_ws"
UNDERLIFT_WS="$HOME/underliftbot_ws"

BT_REPO="https://github.com/BehaviorTree/BehaviorTree.CPP.git"
NAV2_REPO="https://github.com/tasterobotics-vn/navigation2.git"
BT_BRANCH="4.6.2"

UNDERLIFT_SOURCE="$UNDERLIFT_WS/src/underliftbotSim"
echo "============================================================"
echo "       Underliftbot Environment Setup"
echo "============================================================"
echo "ROS distribution: $ROS_DISTRO"
echo "BehaviorTree workspace: $BT_WS"
echo "Navigation2 workspace: $NAV2_WS"
echo "Underliftbot workspace: $UNDERLIFT_WS"
echo "============================================================"

# ============================================================
# 1. Install Gazebo Ionic
# ============================================================

echo ""
echo "[1/7] Installing Gazebo Ionic..."

sudo apt-get update -y
sudo apt-get install -y curl lsb-release gnupg
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y gz-ionic

# ============================================================
# 2. Source ROS 2
# ============================================================

echo ""
echo "[2/7] Loading ROS 2 environment..."

ROS_SETUP="/opt/ros/$ROS_DISTRO/setup.bash"

if [ ! -f "$ROS_SETUP" ]; then
    echo "ERROR: ROS setup file not found: $ROS_SETUP"
    echo "Please install ROS 2 $ROS_DISTRO or set ROS_DISTRO correctly."
    exit 1
fi

source "$ROS_SETUP"

# Check required build tools
if ! command -v colcon >/dev/null 2>&1; then
    echo "Installing colcon build tools..."
    sudo apt-get install -y python3-colcon-common-extensions
fi

if ! command -v rosdep >/dev/null 2>&1; then
    echo "Installing rosdep..."
    sudo apt-get install -y python3-rosdep
fi

# Initialize rosdep if necessary
if ! sudo test -f /etc/ros/rosdep/sources.list.d/20-default.list; then
    sudo rosdep init
fi

rosdep update

# ============================================================
# 3. Build BehaviorTree.CPP 4.6.2
# ============================================================

echo ""
echo "[3/7] Setting up BehaviorTree.CPP..."

mkdir -p "$BT_WS/src"

if [ ! -d "$BT_WS/src/BehaviorTree.CPP/.git" ]; then
    git clone \
        --branch "$BT_BRANCH" \
        --single-branch \
        "$BT_REPO" \
        "$BT_WS/src/BehaviorTree.CPP"
else
    echo "BehaviorTree.CPP already exists. Skipping clone."
fi

cd "$BT_WS"

rosdep install \
    --from-paths src \
    --ignore-src \
    --rosdistro "$ROS_DISTRO" \
    -r -y

colcon build --symlink-install --parallel-workers "$JOBS"

source "$BT_WS/install/setup.bash"

echo "BehaviorTree.CPP build completed."

# ============================================================
# 4. Build custom Navigation2
# ============================================================

echo ""
echo "[4/7] Setting up Navigation2..."

mkdir -p "$NAV2_WS/src"

if [ ! -d "$NAV2_WS/src/navigation2/.git" ]; then
    git clone "$NAV2_REPO" "$NAV2_WS/src/navigation2"
else
    echo "Navigation2 already exists. Skipping clone."
fi

cd "$NAV2_WS"

# Load ROS 2 and BehaviorTree.CPP
source "$ROS_SETUP"
source "$BT_WS/install/setup.bash"

rosdep install \
    --from-paths src \
    --ignore-src \
    --rosdistro "$ROS_DISTRO" \
    -r -y

colcon build \
    --symlink-install \
    --parallel-workers "$JOBS"

source "$NAV2_WS/install/setup.bash"

echo "Navigation2 build completed."

# ============================================================
# 5. Copy Underliftbot simulation into its workspace
# ============================================================

echo ""
echo "[5/7] Checking Underliftbot source directory..."

if [ ! -d "$UNDERLIFT_SOURCE" ]; then
    echo "ERROR: Underliftbot source directory not found:"
    echo "$UNDERLIFT_SOURCE"
    exit 1
fi

echo "Using existing source directory:"
echo "$UNDERLIFT_SOURCE"

# ============================================================
# 6. Install dependencies and build Underliftbot
# ============================================================

echo ""
echo "[6/7] Building Underliftbot..."

cd "$UNDERLIFT_WS"

source "$ROS_SETUP"
source "$BT_WS/install/setup.bash"
source "$NAV2_WS/install/setup.bash"

rosdep install \
    --from-paths src \
    --ignore-src \
    --rosdistro "$ROS_DISTRO" \
    -r -y

colcon build \
    --symlink-install \
    --parallel-workers "$JOBS"

echo "Underliftbot build completed."

# ============================================================
# 7. Configure Gazebo resource paths in ~/.bashrc
# ============================================================

echo ""
echo "[7/7] Configuring Gazebo resource paths..."

GZ_MODELS="$UNDERLIFT_WS/install/underliftbot_description/share/underliftbot_description/models"
GZ_WORLDS="$UNDERLIFT_WS/install/underliftbot_description/share/underliftbot_description/worlds"

GZ_EXPORT='export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:+$GZ_SIM_RESOURCE_PATH:}$HOME/underliftbot_ws/install/underliftbot_description/share/underliftbot_description/models:$HOME/underliftbot_ws/install/underliftbot_description/share/underliftbot_description/worlds"'

# Add the export only if it does not already exist.
if ! grep -Fq 'underliftbot_description/share/underliftbot_description/models' "$HOME/.bashrc"; then
    {
        echo ""
        echo "# Underliftbot Gazebo resource paths"
        echo "$GZ_EXPORT"
    } >> "$HOME/.bashrc"

    echo "Gazebo resource paths added to ~/.bashrc."
else
    echo "Gazebo resource paths already configured in ~/.bashrc."
fi

# ============================================================
# Finish
# ============================================================

echo ""
echo "============================================================"
echo "       Underliftbot Setup Completed Successfully"
echo "============================================================"

echo ""
echo "Workspace locations:"
echo "  BehaviorTree.CPP: $BT_WS"
echo "  Navigation2:      $NAV2_WS"
echo "  Underliftbot:     $UNDERLIFT_WS"

echo ""
echo "To load all workspaces in a new terminal, run:"
echo ""
echo "source /opt/ros/$ROS_DISTRO/setup.bash"
echo "source $BT_WS/install/setup.bash"
echo "source $NAV2_WS/install/setup.bash"
echo "source $UNDERLIFT_WS/install/setup.bash"
echo ""
echo "To apply the Gazebo resource path immediately, run:"
echo "source ~/.bashrc"
echo ""
echo "============================================================"
