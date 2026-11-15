# Drone YOLO Semantic Control

Mô phỏng drone trong ROS 2 Jazzy và Gazebo Harmonic, sử dụng camera RGB-D và YOLO để nhận diện người (`person`), ô tô (`car`) và điều khiển dừng theo khoảng cách.

## 1. Hệ thống hoạt động như thế nào?

| Thành phần                    | Nhiệm vụ                                                                   |
| ----------------------------- | -------------------------------------------------------------------------- |
| `drone_scene`                 | Mở world Gazebo, tạo drone, camera RGB-D và bridge ROS                     |
| `semantic_perception`         | Đồng bộ RGB/depth, chạy YOLO, tính khoảng cách từ depth trong bounding box |
| `semantic_controller`         | Tự cất cánh, bay tiến, giảm tốc và giữ dừng                                |
| `drone_control/run.launch.py` | Chạy cả simulation, perception và controller                               |

Hành vi được cấu hình: tăng độ cao **1,1 m so với vị trí spawn**, bay theo +X thân drone ở **0,25 m/s**, dừng trước người **2 m**, trước xe **1 m**. Khoảng cách là xấp xỉ theo hướng bay tới mặt trước drone, có biên 0,1 m và bù độ trễ ảnh nên có thể dừng sớm hơn ngưỡng.

**Giới hạn hiện tại:** người/xe trong cảnh được dựng từ primitive SDF; chưa xác nhận YOLO pretrained nhận diện ổn định. Build và kiểm thử logic thành công chưa chứng minh demo dừng đúng theo lớp. Drone dùng điều khiển vận tốc, tắt trọng lực; chưa phải mô hình bay với autopilot, chưa né tránh hay lập kế hoạch đường đi.

## 2. Chuẩn bị trước khi cài

- Ubuntu 24.04, ROS 2 Jazzy, Python hệ thống 3.12.
- Terminal Bash; các lệnh dưới đây bắt đầu ở **thư mục gốc repository**, nơi có file README này và thư mục `ros_ws`.
- Có mạng khi cài dependency và tải weights lần đầu.
- Có môi trường đồ họa để mở cửa sổ Gazebo.

Nếu chưa cài ROS 2 Jazzy và cấu hình kho apt ROS, hoàn thành hướng dẫn chính thức trước:
[ROS 2 Jazzy trên Ubuntu](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
Sau đó làm lần lượt các bước 3 → 4 → 5 → 6.

## 3. Cài các gói ROS và công cụ hệ thống — lần đầu

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher ros-jazzy-cv-bridge \
  ros-jazzy-message-filters ros-jazzy-rqt-image-view \
  python3-colcon-common-extensions python3-rosdep python3-venv \
  python3-pytest
source /opt/ros/jazzy/setup.bash
```

Cài dependency khai báo trong hai package bằng rosdep:

```bash
# Chỉ chạy dòng này nếu máy chưa khởi tạo rosdep:
sudo rosdep init

rosdep update
rosdep install --from-paths ros_ws/src --ignore-src -r -y --rosdistro jazzy
```

Nếu `rosdep init` báo đã tồn tại cấu hình, tiếp tục `rosdep update`, không cần khởi tạo lại.
`ros-jazzy-ros-gz` cung cấp tích hợp ROS/Gazebo; kiểm tra simulator trước khi chạy:

```bash
gz sim --help
ros2 pkg prefix ros_gz_sim
ros2 pkg prefix ros_gz_bridge
```

## 4. Cài YOLO và tải weights — chọn một cách

### Cách A: dùng script có sẵn

Từ thư mục gốc repository:

```bash
bash ros_ws/src/drone_control/scripts/setup_yolo.sh
```

Script tạo `.venv` bằng Python hệ thống với `--system-site-packages`, cài PyTorch CPU, torchvision, Ultralytics và tải `models/yolov8n.pt`.
World, mesh và model cảnh đã nằm trong repository, không cần tải riêng.

### Cách B: cài thủ công

Cách này tương đương script; không cần thực hiện cả hai cách.

```bash
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install torch torchvision \
  --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r ros_ws/src/drone_control/requirements.txt
mkdir -p models
(cd models && YOLO_CONFIG_DIR="$PWD/../.venv/yolo-config" \
  ../.venv/bin/python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')")
```

Dự án giới hạn `numpy<2` và `opencv-python<4.12` để tương thích với ROS `cv_bridge`.
Không dùng `sudo pip install`. Có thể dùng weights tự huấn luyện nếu tên lớp là `person` và `car`; truyền đường dẫn qua `weights:=...`. Node yêu cầu weights có sẵn, không tự tải trong khi bay.

## 5. Build workspace

Dùng terminal chưa activate venv để colcon sử dụng Python hệ thống của ROS:

```bash
source /opt/ros/jazzy/setup.bash
cd ros_ws
colcon build --symlink-install --packages-select drone_scene drone_control
cd ..
source ros_ws/install/setup.bash
```

Khi sửa code, build lại nếu cần và source lại workspace. Không cần cài lại YOLO mỗi lần chạy.

## 6. Chạy toàn bộ bằng ros2 launch

### 6.1. Thiết lập terminal — thực hiện mỗi lần mở terminal chạy demo

Tại thư mục gốc repository:

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
export PYTHONPATH="$PWD/.venv/lib/python3.12/site-packages:${PYTHONPATH:-}"
export YOLO_CONFIG_DIR="$PWD/.venv/yolo-config"
```

`PYTHONPATH` giúp các ROS entry point dùng Python hệ thống tìm được YOLO trong venv.

### 6.2. Demo người: tự cất cánh, bay tiến và dừng

```bash
ros2 launch drone_control run.launch.py weights:="$PWD/models/yolov8n.pt"
```

Lệnh mở Gazebo, camera, YOLO và controller. Drone spawn ở `(-7, 1.5, 0.15)` m, người trên vạch qua đường ở `(0, 1.5)` m. Theo dõi ảnh và trạng thái ở bước 7 để xác định YOLO có thực sự nhận diện người hay không.

### 6.3. Demo ô tô

Dừng phiên trước bằng `Ctrl+C`, chờ các process thoát rồi chạy:

```bash
ros2 launch drone_control run.launch.py \
  weights:="$PWD/models/yolov8n.pt" x:=2.5
```

Drone xuất phát sau vị trí người trên đường, hướng về xe ở `(7, 1.5)` m.
Không chạy hai simulation hoặc hai controller phát `/cmd_vel` cùng lúc.

### 6.4. Cách chạy ngắn bằng script

Sau khi đã cài đặt và build, script thiết lập môi trường rồi gọi cùng launch ở trên:

```bash
bash ros_ws/src/drone_control/scripts/run_demo.sh
# Hoặc demo xe, sau khi đóng phiên trước:
bash ros_ws/src/drone_control/scripts/run_demo.sh x:=2.5
```

## 7. Xem camera, nhận diện và trạng thái

Mở terminal khác tại thư mục gốc; mỗi terminal quan sát cần source:

```bash
source /opt/ros/jazzy/setup.bash
source ros_ws/install/setup.bash
```

Xem ảnh, chọn topic `/semantic/annotated` trong giao diện:

```bash
ros2 run rqt_image_view rqt_image_view
```

Có thể chọn `/front_rgbd/image` hoặc `/front_rgbd/depth_image` để xem cảm biến gốc.
Dùng terminal khác để theo dõi:

```bash
ros2 topic echo /semantic/status
```

| Trạng thái                                    | Ý nghĩa                                                  |
| --------------------------------------------- | -------------------------------------------------------- |
| `WAIT_ODOMETRY`                               | Chưa có odometry mới, phát vận tốc zero                  |
| `TAKEOFF`                                     | Đang tăng độ cao, chưa bay tiến                          |
| `WAIT_PERCEPTION`                             | Chưa có kết quả perception đủ mới                        |
| `WAIT_DEPTH` / `WAIT_OBJECT_DEPTH`            | Thiếu depth hợp lệ                                       |
| `CRUISE` / `APPROACH_person` / `APPROACH_car` | Bay tiến hoặc giảm tốc                                   |
| `HOLD_ALTITUDE`                               | Tạm ngừng bay tiến để chỉnh độ cao                       |
| `STOP_person` / `STOP_car`                    | Dừng theo lớp nhận diện                                  |
| `STOP_OBSTACLE`                               | Dừng do depth vật cản gần, chưa chứng minh dừng theo lớp |
| `STOP_MAX_TRAVEL`                             | Đạt giới hạn quãng đường                                 |

`/semantic/detections` là JSON trong `std_msgs/String`, gồm timestamp ảnh, `objects` với `class`, `confidence`, `bbox`, `distance_m`, `in_path`, và `obstacle_m`.
`/semantic/status` chứa trạng thái, vận tốc và dữ liệu nhận diện đã dùng.

Sau trạng thái `STOP_*`, controller giữ dừng. Để bỏ chốt dừng:

```bash
ros2 service call /semantic/reset std_srvs/srv/Trigger '{}'
```

Nếu vật cản còn đó, drone có thể dừng lại ngay. Muốn bắt đầu lại từ vị trí ban đầu, đóng demo và launch lại.

Ghi dữ liệu để kiểm chứng:

```bash
ros2 bag record /front_rgbd/image /front_rgbd/depth_image \
  /semantic/detections /semantic/status /cmd_vel /odom /clock
```

Rosbag được lưu trong thư mục hiện tại; nhấn `Ctrl+C` để kết thúc ghi.
Đánh giá riêng từng lớp bằng ảnh annotated, confidence, khoảng cách và vận tốc tại thời điểm dừng. Trong logic, cùng khoảng cách 1,8 m, người yêu cầu dừng còn xe có thể tiếp tục nếu đường an toàn.

## 8. Chạy mô phỏng riêng hoặc tách hai terminal

### Chỉ mở cảnh, không tự bay và không chạy YOLO

```bash
ros2 launch drone_scene sim.launch.py
```

Scene riêng mặc định spawn ở `(-11, 1.5, 0.15)` m, khác vị trí mặc định của demo đầy đủ.

### Mở scene trước, controller sau

Terminal 1, sau khi source môi trường:

```bash
ros2 launch drone_scene sim.launch.py x:=-7 y:=1.5 z:=0.15
```

Terminal 2, thực hiện thiết lập ở mục 6.1 rồi chạy:

```bash
ros2 launch drone_control run.launch.py \
  start_sim:=false weights:="$PWD/models/yolov8n.pt"
```

### Mở world phòng kín cũ

```bash
ros2 launch drone_scene sim.launch.py world:=arena.sdf x:=0 y:=0 z:=1.2
```

Đây là lệnh mở scene riêng. Có thể truyền `world`, `x`, `y`, `z` và `gz_extra_args` cho launch đầy đủ khi cần. Chạy không giao diện bằng `gz_extra_args:='-s --headless-rendering'` vẫn cần môi trường hỗ trợ render camera.

## 9. Cấu hình và bố trí cảnh

Tham số controller/perception nằm trong `ros_ws/src/drone_control/config/semantic.yaml`:

| Tham số                            | Mặc định  | Ý nghĩa                                    |
| ---------------------------------- | --------- | ------------------------------------------ |
| `takeoff_height`                   | 1.1       | Độ cao tăng thêm so với spawn, m           |
| `cruise_speed`                     | 0.25      | Vận tốc tiến, m/s                          |
| `person_distance` / `car_distance` | 2.0 / 1.0 | Ngưỡng dừng theo lớp, m                    |
| `stop_margin`                      | 0.10      | Biên dừng bổ sung, m                       |
| `perception_timeout`               | 1.0       | Tuổi tối đa của kết quả perception, s      |
| `max_travel`                       | 20.0      | Giới hạn độ dời ngang từ điểm xuất phát, m |
| `confidence`                       | 0.35      | Ngưỡng confidence YOLO                     |
| `inference_hz`                     | 5.0       | Tần suất gọi inference mong muốn           |
| `device`                           | cpu       | Thiết bị inference                         |

Controller chạy 20 Hz, RGB/depth đồng bộ với slop 60 ms; depth camera trước có tầm xa 10 m. Depth foreground được ước lượng bằng percentile 20 trong vùng giữa bounding box, loại giá trị không hợp lệ. Vùng giữa ảnh dùng để xấp xỉ đường bay; chưa tái dựng hình học 3D đầy đủ.

World ngoài trời rộng 36 × 28 m, có đường, vạch qua đường, vỉa hè, bãi đỗ, 3 người, 3 xe và 5 cây; các vật thể đứng yên, có collision.

| Model                      | Vị trí gốc (m)                                |
| -------------------------- | --------------------------------------------- |
| `person_crossing`          | (0, 1.5, 0.055)                               |
| `person_sidewalk`          | (-5, 4.2, 0.16)                               |
| `person_parking`           | (4.5, -4, 0.04)                               |
| `car_road`                 | (7, 1.5, 0.04)                                |
| `car_park_1`, `car_park_2` | (1.5, -6, 0.04), (7.5, -6, 0.04)              |
| `tree_1` … `tree_5`        | (-10, 8), (-3, 8), (5, 8), (12, 8), (-10, -7) |

Chỉnh vị trí trong `ros_ws/src/drone_scene/worlds/semantic_outdoor.sdf`, hình dáng trong `ros_ws/src/drone_scene/models/demo_person`, `demo_sedan`, `demo_tree`.
Generator bên dưới **ghi đè ba model và world ngoài trời**; sửa generator trước nếu muốn giữ thay đổi khi tái tạo:

```bash
python3 ros_ws/src/drone_scene/scripts/generate_outdoor_world.py
```

Tên world nội bộ vẫn là `e2es_indoor` để dùng chung bridge với phòng cũ.

## 10. Kiểm tra code

Từ thư mục gốc, dùng Python hệ thống và ROS environment:

```bash
source /opt/ros/jazzy/setup.bash
PYTHONPATH="$PWD/ros_ws/src/drone_control:$PYTHONPATH" \
  /usr/bin/python3 -m pytest \
  ros_ws/src/drone_control/test/test_policy.py \
  ros_ws/src/drone_control/test/test_controller.py -q
```

Các test kiểm tra logic khoảng cách, cất cánh, giữ dừng và xử lý dữ liệu thiếu/cũ.
Lần kiểm tra trước đã build thành công hai package và đạt 10 test logic/controller. Chưa chạy kiểm chứng chuyến bay đầy đủ vì môi trường kiểm tra thiếu `gz` và weights; không xem kết quả test là bằng chứng nhận diện thành công trong Gazebo.

## 11. Xử lý lỗi thường gặp

| Hiện tượng                                     | Cách kiểm tra / xử lý                                                                                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ros2: command not found`                      | Source `/opt/ros/jazzy/setup.bash`                                                                                                                     |
| Không tìm thấy `drone_scene` / `drone_control` | Build bước 5 rồi source `ros_ws/install/setup.bash` trong terminal đang dùng                                                                           |
| `gz: command not found`                        | Kiểm tra bước 3 và cài đặt Gazebo/ROS-Gazebo trước khi chạy                                                                                            |
| Không tìm thấy `ultralytics`                   | Làm bước 4 và export `PYTHONPATH` ở mục 6.1                                                                                                            |
| Không có weights                               | Kiểm tra `ls models/yolov8n.pt`, chạy setup hoặc truyền đường dẫn weights thật                                                                         |
| Lỗi NumPy / cv_bridge                          | Dùng Python 3.12 hệ thống, venv có system site packages và cài đúng requirements                                                                       |
| `WAIT_ODOMETRY`                                | Kiểm tra simulation đang chạy, không pause; dùng `ros2 topic hz /odom` và kiểm tra `/clock`                                                            |
| `WAIT_PERCEPTION`                              | Kiểm tra log YOLO, `ros2 topic hz /front_rgbd/image`, `/front_rgbd/depth_image`, `/semantic/detections`; inference CPU quá chậm cũng làm kết quả bị cũ |
| `WAIT_DEPTH`                                   | Kiểm tra ảnh depth; vật thể có thể ngoài tầm 10 m hoặc vùng đo không có depth hợp lệ                                                                   |
| YOLO không có bounding box người/xe            | Xem `/semantic/annotated`; cân nhắc mesh có texture hoặc fine-tune trên ảnh mô phỏng, không dùng tên model Gazebo giả nhãn                             |
| Drone giữ dừng                                 | Xem trạng thái; reset chốt ở bước 7 hoặc khởi động lại demo                                                                                            |
| Không thấy drone trong cửa sổ                  | Chọn `semantic_drone` trong Entity Tree và đưa camera tới model                                                                                        |

Takeoff chỉ bay thẳng đứng và không đợi YOLO; sau đó cần perception mới để bay tiến. Mất odometry phát zero; thiếu depth hoặc perception quá cũ sẽ ngăn bay tiến. Vật cản chưa phân loại có ngưỡng depth khẩn cấp 0,65 m cùng bù độ trễ; `STOP_OBSTACLE` không phải thành công nhận diện người/xe.

Kết thúc bình thường bằng `Ctrl+C`. Plugin vận tốc chưa có watchdog riêng cho trường hợp controller bị `SIGKILL`; nếu cưỡng bức tắt process, pause hoặc dừng Gazebo.
