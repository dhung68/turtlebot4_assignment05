#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source /opt/ros/humble/setup.bash
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r scripts/requirements-yolo.txt
.venv/bin/python scripts/check_environment.py
