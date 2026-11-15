# Drone YOLO Semantic Control

A ROS 2 Jazzy and Gazebo Harmonic simulation combining RGB-D sensing, YOLO object detection, and distance-based drone control.

The drone takes off, moves forward, and stops based on the detected object class: **2 m before a person** or **1 m before a car**. Depth sensing also provides an emergency obstacle stop.

## How it works

`Gazebo RGB-D camera → YOLO + depth estimation → semantic controller → velocity commands`

- **drone_scene:** outdoor world, drone, front RGB-D camera, and ROS–Gazebo bridges.
- **drone_control:** synchronized RGB/depth perception, automatic takeoff, forward motion, and latched stopping.
- **Scene:** a road, crosswalk, sidewalks, parking area, three people, three cars, and five trees.

## Requirements

Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, system Python 3.12, and a graphical environment. Install [ROS 2 Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) first. Internet access is needed for dependencies and the initial model download.

Run the following commands in Bash from the repository root.

## Setup

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher ros-jazzy-cv-bridge \
  ros-jazzy-message-filters ros-jazzy-rqt-image-view \
  python3-colcon-common-extensions python3-rosdep python3-venv python3-pytest
source /opt/ros/jazzy/setup.bash

# Run only if rosdep has not been initialized:
sudo rosdep init
rosdep update
rosdep install --from-paths ros_ws/src --ignore-src -r -y --rosdistro jazzy

# Create .venv, install CPU PyTorch and YOLO, and download models/yolov8n.pt.
bash ros_ws/src/drone_control/scripts/setup_yolo.sh

# Build using the system Python; leave the virtual environment inactive.
cd ros_ws
colcon build --symlink-install --packages-select drone_scene drone_control
cd ..
```

The setup script uses system site packages and pins NumPy/OpenCV for ROS `cv_bridge` compatibility. Scene assets are included in the repository.

## Run

```bash
# Person demo: take off, move forward, and stop.
bash ros_ws/src/drone_control/scripts/run_demo.sh

# Car demo: close the previous demo with Ctrl+C before starting this one.
bash ros_ws/src/drone_control/scripts/run_demo.sh x:=4.0 y:=-6.0
```

The default spawn position is **`(-5, 1.5, 0.15)` m**, facing the person at `(0, 1.5)` m. The car demo spawns at `(4.0, -6.0, 0.15)` m, facing the parked car at `(7.5, -6)` m.

The script sources ROS and the workspace, exposes the YOLO environment, and launches simulation, perception, and control. Stop with `Ctrl+C`; run one demo at a time.

To launch manually or use custom weights with class names `person` and `car`:

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
export PYTHONPATH="$PWD/.venv/lib/python3.12/site-packages:${PYTHONPATH:-}"
export YOLO_CONFIG_DIR="$PWD/.venv/yolo-config"
ros2 launch drone_control run.launch.py weights:="$PWD/models/yolov8n.pt"
```

For the scene alone, with the same default spawn position, source ROS and the workspace, then run:

```bash
ros2 launch drone_scene sim.launch.py
```

## Observe and configure

In another terminal, source ROS and the workspace, then run:

```bash
ros2 run rqt_image_view rqt_image_view   # Select /semantic/annotated.
ros2 topic echo /semantic/status       # Run in a separate terminal.
```

Detections are published as JSON on `/semantic/detections`. `STOP_person` and `STOP_car` indicate class-based stopping; `STOP_OBSTACLE` indicates a depth-only stop. Stops remain latched until reset or restart:

```bash
ros2 service call /semantic/reset std_srvs/srv/Trigger '{}'
```

Edit [`semantic.yaml`](ros_ws/src/drone_control/config/semantic.yaml) to tune behavior:

| Parameter | Default |
| --- | --- |
| Takeoff height above spawn | 1.1 m |
| Forward speed | 0.25 m/s |
| Person / car stop distance | 2.0 / 1.0 m |
| Additional stop margin | 0.10 m |
| Maximum horizontal displacement | 20 m |
| YOLO confidence / inference rate | 0.35 / 5 Hz |
| Inference device | CPU |

Distances are approximate forward clearances; margins and image latency compensation can cause earlier stops. Scene layout is defined in [`semantic_outdoor.sdf`](ros_ws/src/drone_scene/worlds/semantic_outdoor.sdf).

## Tests

```bash
source /opt/ros/jazzy/setup.bash
PYTHONPATH="$PWD/ros_ws/src/drone_control:${PYTHONPATH:-}" \
  /usr/bin/python3 -m pytest \
  ros_ws/src/drone_control/test/test_policy.py \
  ros_ws/src/drone_control/test/test_controller.py -q
```

These tests cover control logic, including distance thresholds, takeoff, latched stops, and missing or stale data. They do not verify end-to-end detection in Gazebo.

## Limitations

People and cars use primitive SDF geometry; reliable recognition by pretrained YOLO has **not been confirmed**. Validate annotated images and detection/status topics before claiming successful class-based stopping.

The drone uses velocity control with gravity disabled. This is a simulation prototype without an autopilot, obstacle avoidance, or path planning. Missing or stale perception/depth prevents forward motion; missing odometry commands zero velocity. If the controller is forcibly killed, pause or stop Gazebo because the velocity plugin has no independent watchdog.
