# TurtleBot 4 — Nav2 + YOLO

## Cài đặt

Yêu cầu Ubuntu 22.04, ROS 2 Humble và TurtleBot 4 Simulator/Gazebo Fortress đã cài.

```bash
git clone https://github.com/dhung68/turtlebot4_assignment05.git
cd turtlebot4_assignment05
sudo apt update
xargs -r -a scripts/apt-packages.txt sudo apt install -y
bash scripts/setup_dependencies.sh
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/download_assets.py
bash scripts/build.sh
```

## Chạy

Mỗi terminal mở tại thư mục repository và chạy trước:

```bash
source scripts/env.sh
```

**Terminal 1 — Gazebo:**

```bash
ros2 launch tb4_yolo_demo simulation.launch.py
```

Chờ world và robot xuất hiện, bấm Play nếu đang pause. Lần đầu cần Internet để tải world.

**Terminal 2 — Bản đồ, AMCL và Nav2:**

```bash
ros2 launch tb4_yolo_demo navigation.launch.py
```

**Terminal 3 — RViz:**

```bash
ros2 launch tb4_yolo_demo rviz.launch.py
```

Máy NVIDIA hybrid: thêm `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia` trước lệnh Gazebo/RViz nếu cần.

**Terminal 4 — Initial pose, người 3D và YOLO:**

Robot vừa spawn mặc định trên dock, chưa di chuyển:

```bash
.venv/bin/python scripts/initial_pose.py --x 0 --y 0 --yaw 0
ros2 lifecycle get /amcl
ros2 lifecycle get /bt_navigator
```

Chờ cả hai node `active [3]`, kiểm tra laser khớp bản đồ. Nếu robot đã di chuyển, dùng **2D Pose Estimate** để đặt đúng pose.

```bash
ros2 run tb4_yolo_demo spawn_objects --asset-dir "$PWD/assets/standing_person" --config "$PWD/src/tb4_yolo_demo/config/objects.yaml"
ros2 launch tb4_yolo_demo perception.launch.py weights:="$PWD/models/yolov8n.pt"
```

Chỉ spawn người một lần mỗi phiên. Xem `/yolo/annotated_image` trên RViz với QoS **Best Effort**. Thêm `device:=cpu` vào lệnh perception để chạy CPU.

**Terminal 5 — Mission:**

```bash
ros2 launch tb4_yolo_demo mission.launch.py localization_confirmed:=true
```

Robot tự undock và đi lần lượt ba goal trong `src/tb4_yolo_demo/config/goals.yaml`. Không điều khiển tay hoặc đặt lại pose trong mission.

Kết quả: `evidence/runtime/mission_*.json`. Kiểm tra cả ba goal `SUCCEEDED`.

Dừng bằng **Ctrl+C** tại terminal mission, kiểm tra robot đã dừng rồi đóng các launch còn lại. Không chạy trùng simulator/Nav2 hoặc chạy SLAM cùng AMCL.

## Depot v6 tùy chọn

Nếu world không khớp bản đồ, tải đúng Depot v6:

```bash
mkdir -p assets/depot_v6
curl -fL --retry 3 'https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot/6/Depot.zip' -o assets/depot-v6.zip
unzip -n assets/depot-v6.zip -d assets/depot_v6
```

Thay lệnh Gazebo bằng:

```bash
ros2 launch tb4_yolo_demo simulation.launch.py depot_asset:="$PWD/assets/depot_v6"
```

Giấy phép/nguồn: [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
