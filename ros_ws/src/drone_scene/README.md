# Môi trường thử nghiệm drone và nhận diện ngữ nghĩa

Mặc định `sim.launch.py` mở `worlds/semantic_outdoor.sdf`: khuôn viên 36 × 28 m,
đường hai chiều, vạch qua đường, vỉa hè, bãi đỗ, 3 ô tô, 3 người và 5 cây.
Tất cả tài nguyên mới đều nằm trong package, không tải model từ Internet.
World phòng kín cũ `arena.sdf` vẫn được giữ lại.

## Chạy (ROS 2 Jazzy + Gazebo Sim Harmonic)

Máy cần có Gazebo Harmonic (`gz sim`), `ros_gz_sim`, `ros_gz_bridge`,
`robot_state_publisher` và `xacro`.

Từ thư mục gốc repository:

```bash
source /opt/ros/jazzy/setup.bash
cd ros_ws
colcon build --symlink-install --packages-select drone_scene
source install/setup.bash
ros2 launch drone_scene sim.launch.py
```

Drone xuất hiện tại `(-11, 1.5, 0.15)` m, nhìn theo +X. Chọn model trong Entity Tree
và dùng chức năng di chuyển camera tới model nếu khung nhìn ban đầu chưa bao quát cảnh.
Dùng `rqt_image_view` hoặc RViz xem `/front_rgbd/image` và `/front_rgbd/depth_image`.
Depth camera trước có tầm xa 10 m, nên vật thể xa hơn sẽ chưa có depth hợp lệ.
Launch scene này không tự chạy YOLO hoặc controller. Dùng `drone_control/run.launch.py`
để tự cất cánh và dừng theo nhận diện; xem README của gói drone_control.
Drone dùng VelocityControl và tắt trọng lực để giữ độ cao khi không có lệnh;
đây là mô phỏng điều khiển vận tốc, chưa phải mô hình động lực học bay với autopilot.

Ví dụ mở lại phòng cũ (phải đổi vị trí spawn):

```bash
ros2 launch drone_scene sim.launch.py world:=arena.sdf x:=0 y:=0 z:=1.2
```

## Bố trí để thử từng đối tượng

| Đối tượng | Tọa độ gốc (m) | Gợi ý |
|---|---|---|
| person_crossing | (0, 1.5, 0.055) | Drone mặc định nhìn về người trên vạch qua đường |
| person_sidewalk | (-5, 4.2, 0.16) | Người trên vỉa hè |
| person_parking | (4.5, -4, 0.04) | Người trong bãi xe |
| car_road | (7, 1.5, 0.04) | Thử riêng xe bằng vị trí spawn bên dưới |
| car_park_1 / car_park_2 | (1.5, -6, 0.04) / (7.5, -6, 0.04) | Hai xe đỗ |
| tree_1 … tree_5 | (-10, 8), (-3, 8), (5, 8), (12, 8), (-10, -7) | Vật cản có thân và tán cây |

Thử riêng xe trên đường, không có người phía trước:

```bash
ros2 launch drone_scene sim.launch.py x:=2.5 y:=1.5 z:=1.2
```

Các đối tượng hiện đứng yên, có collision cho cảm biến depth và va chạm.
Model ô tô có thân, cabin kính, bánh, đèn; người có đầu, thân, tay, chân.
Chúng được dựng từ primitive SDF, không phải model quét hoặc ảnh chân thực.
**Chưa xác nhận YOLO pretrained nhận ra các model này.** Nếu không nhận ổn định,
cần thay visual của `demo_person`/`demo_sedan` bằng mesh có texture thực tế
hoặc huấn luyện thêm trên dữ liệu mô phỏng. Collision có thể giữ riêng để đo khoảng cách.
Không dùng tên model trong Gazebo làm nhãn đầu vào cho bộ điều khiển YOLO.

Để chứng minh ngưỡng người 2 m / ô tô 1 m, cần bộ điều khiển đọc lớp YOLO và depth
hợp lệ trong bounding box rồi phát `/cmd_vel`, cùng cơ chế an toàn cho vật cản khác.
Nên lấy median depth trong vùng đối tượng, loại NaN/Inf và phân biệt khoảng cách
camera tới bề mặt với khoảng cách tâm drone. Cần ghi lại lớp, confidence, khoảng
cách và lệnh vận tốc khi thử từng trường hợp; việc dựng world chưa kiểm chứng ngưỡng dừng.

## Chỉnh sửa

- Vị trí model: sửa các `<include><pose>` trong `worlds/semantic_outdoor.sdf`.
- Hình dáng: sửa `models/demo_person/model.sdf`, `models/demo_sedan/model.sdf`,
  `models/demo_tree/model.sdf`.
- Có thể tái tạo toàn bộ tài nguyên mới bằng
  `python3 ros_ws/src/drone_scene/scripts/generate_outdoor_world.py` từ gốc repo.
  Lệnh này ghi đè ba model và world mới, nên sửa generator nếu muốn giữ thay đổi.
- Tên world nội bộ vẫn là `e2es_indoor` để dùng chung bridge `/clock` của phòng cũ.
