#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source /opt/ros/humble/setup.bash
.venv/bin/python /usr/bin/colcon build --symlink-install --packages-select tb4_yolo_demo
head -n 1 install/tb4_yolo_demo/lib/tb4_yolo_demo/yolo_detector
