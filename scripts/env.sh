#!/usr/bin/env bash
# Source this file from the workspace root.
source /opt/ros/humble/setup.bash
source install/setup.bash
export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/scripts/fastdds_udp.xml"
export YOLO_CONFIG_DIR="$PWD/.cache/ultralytics"
export ROS_LOG_DIR="$PWD/logs"
mkdir -p "$ROS_LOG_DIR"
