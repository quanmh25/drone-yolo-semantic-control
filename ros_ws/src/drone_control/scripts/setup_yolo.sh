#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
/usr/bin/python3 -m venv --system-site-packages "$repo_dir/.venv"
"$repo_dir/.venv/bin/python" -m pip install torch torchvision \
  --index-url https://download.pytorch.org/whl/cpu
"$repo_dir/.venv/bin/python" -m pip install \
  -r "$repo_dir/ros_ws/src/drone_control/requirements.txt"
mkdir -p "$repo_dir/models"
cd "$repo_dir/models"
YOLO_CONFIG_DIR="$repo_dir/.venv/yolo-config" \
  "$repo_dir/.venv/bin/python" -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
