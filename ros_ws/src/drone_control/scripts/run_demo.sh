#!/usr/bin/env bash
set -eo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
weights_path="$repo_dir/models/yolov8n.pt"
if [[ ! -f "$weights_path" || ! -d "$repo_dir/.venv" ]]; then
  echo 'Chạy bash ros_ws/src/drone_control/scripts/setup_yolo.sh trước.' >&2
  exit 1
fi
source /opt/ros/jazzy/setup.bash
source "$repo_dir/ros_ws/install/setup.bash"
export PYTHONPATH="$repo_dir/.venv/lib/python3.12/site-packages:${PYTHONPATH:-}"
export YOLO_CONFIG_DIR="$repo_dir/.venv/yolo-config"
exec ros2 launch drone_control run.launch.py "weights:=$weights_path" "$@"
