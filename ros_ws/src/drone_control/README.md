# Drone: cất cánh, YOLO RGB-D, dừng theo lớp

`drone_scene/sim.launch.py` chịu trách nhiệm Gazebo, spawn drone và ROS bridge.
`drone_control/run.launch.py` mở simulation đó rồi chạy hai process riêng:

- `semantic_perception`: đồng bộ RGB/depth (slop 60 ms), chạy YOLO trên RGB thật,
  giữ `person` và `car`, lấy depth foreground trong vùng giữa bounding box.
- `semantic_controller`: điều khiển 20 Hz, tăng độ cao 1.1 m so với vị trí spawn,
  bay thẳng theo trục +X thân drone ở 0.25 m/s, giảm tốc rồi dừng trước người 2 m,
  trước ô tô 1 m. Không sử dụng tên model hoặc ground truth Gazebo để phân loại.

Các tham số nằm ở `config/semantic.yaml`. Khoảng cách được xấp xỉ từ camera depth
sang khoảng cách theo hướng bay tới mặt trước drone với góc camera hiện tại 0.3 rad.
Có biên an toàn 0.1 m và bù độ trễ ảnh; do đó drone thường dừng sớm hơn ngưỡng một ít.
Đây không phải phép đo khoảng cách Euclid chính xác tới mesh; cần đo thực nghiệm.

## Chạy nhanh từ thư mục gốc repository

```bash
# Cần mạng: cài PyTorch CPU + YOLO và tải yolov8n.pt một lần.
bash ros_ws/src/drone_control/scripts/setup_yolo.sh
source /opt/ros/jazzy/setup.bash
cd ros_ws
colcon build --packages-select drone_scene drone_control
cd ..
bash ros_ws/src/drone_control/scripts/run_demo.sh
# Demo xe: đóng phiên trước, chạy lại với x:=2.5
bash ros_ws/src/drone_control/scripts/run_demo.sh x:=2.5
```

Script chạy dùng weights ở `models/yolov8n.pt`, dependency trong `.venv`.
Nếu đã có model khác, dùng launch trực tiếp như bên dưới.

## Cài dependency và model

ROS 2 Jazzy, Gazebo Harmonic và các dependency trong package.xml phải có sẵn.
Dùng Python hệ thống của ROS (Ubuntu Jazzy: `/usr/bin/python3`, Python 3.12).

```bash
source /opt/ros/jazzy/setup.bash
/usr/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r ros_ws/src/drone_control/requirements.txt
mkdir -p models
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
# Lệnh trên tải weights vào thư mục hiện tại; chuyển vào models nếu muốn.
```

Node bắt buộc nhận đường dẫn file weights có thật; không tự tải weights khi đang bay.
Có thể dùng weights đã fine-tune nhưng class names phải là `person` và `car`.
Khi chạy ROS entry point được build bằng Python hệ thống, thêm site-packages của venv
vào PYTHONPATH để node nhìn thấy Ultralytics:

```bash
export PYTHONPATH="$PWD/.venv/lib/python3.12/site-packages:$PYTHONPATH"
cd ros_ws
colcon build --symlink-install --packages-select drone_scene drone_control
source install/setup.bash
```

## Demo người / ô tô

Từ `ros_ws`, thay đường dẫn weights cho đúng vị trí thực tế:

```bash
# Người trên vạch qua đường tại (0, 1.5). Spawn trên mặt đất, tự cất cánh.
ros2 launch drone_control run.launch.py weights:=/absolute/path/yolov8n.pt

# Đóng phiên trước rồi chạy demo xe, không có người chắn giữa đường:
ros2 launch drone_control run.launch.py weights:=/absolute/path/yolov8n.pt x:=2.5
```

Chạy simulation riêng nếu muốn:

```bash
ros2 launch drone_scene sim.launch.py x:=-7 y:=1.5 z:=0.15
# Terminal khác, cùng ROS/Python environment:
ros2 launch drone_control run.launch.py start_sim:=false weights:=/absolute/path/yolov8n.pt
```

Không chạy hai simulation hoặc hai node phát `/cmd_vel` cùng lúc.

## Quan sát và chứng minh tác dụng YOLO

```bash
ros2 run rqt_image_view rqt_image_view  # chọn /semantic/annotated
ros2 topic echo /semantic/status
ros2 bag record /front_rgbd/image /front_rgbd/depth_image /semantic/detections /semantic/status /cmd_vel /odom /clock
```

`/semantic/detections` là JSON trong `std_msgs/String`, gồm timestamp ảnh, danh sách
`class`, `confidence`, `bbox`, `distance_m`, `in_path`, và `obstacle_m`.
`/semantic/status` chứa trạng thái, lệnh vận tốc và kết quả nhận diện dùng để quyết định.
Ở cùng khoảng cách 1.8 m, `person` yêu cầu dừng còn `car` vẫn được tiến nếu đường an toàn.
Kiểm tra logic này bằng `python -m pytest ros_ws/src/drone_control/test/test_policy.py`
với source package trong PYTHONPATH hoặc sau khi build/source workspace.

Sau `STOP_person`, `STOP_car`, `STOP_OBSTACLE` hoặc `STOP_MAX_TRAVEL`, giữ dừng
cho tới khi gọi `ros2 service call /semantic/reset std_srvs/srv/Trigger '{}'`.
Nếu vật cản vẫn ở đó drone sẽ dừng lại ngay. Depth không hợp lệ, mất nhận diện quá 1 s
hoặc mất odometry sẽ không cho bay tiến. Takeoff không đợi YOLO nhưng chỉ bay thẳng đứng;
sau takeoff phải có dữ liệu nhận diện mới được tiến. Mất odom sẽ phát vận tốc zero.
Không suy luận lại ảnh cũ để giả heartbeat. Chạy inference CPU quá chậm cũng khiến drone
chờ; có thể chỉnh tốc độ infer, model/device và timeout sau khi đo độ trễ thực tế.

Cảnh hiện tại dùng model người/xe từ primitive. **Chưa xác nhận YOLO pretrained nhận ra**
chúng ổn định. Nếu không nhận, phải thay visual bằng mesh có texture hoặc fine-tune;
không có fallback giả nhãn. Depth vẫn dừng khẩn cấp ở 0.65 m cho vật cản chưa phân loại,
nhưng đó không được báo cáo là thành công của ngưỡng ngữ nghĩa 2 m/1 m.

Giới hạn: bay thẳng, chưa lập kế hoạch né tránh, chưa bám người, chưa mô phỏng autopilot.
Dùng corridor ảnh giữa để chọn vật thể chắn đường, chưa tái dựng hình học 3D đầy đủ.
Shutdown bình thường phát zero; plugin vận tốc hiện tại không có watchdog riêng khi
process bị SIGKILL, nên dừng/pause Gazebo nếu cưỡng bức tắt controller.

API YOLO được đối chiếu với tài liệu chính thức: https://docs.ultralytics.com/modes/predict/
