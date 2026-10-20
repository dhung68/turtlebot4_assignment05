# Assignment 05 — TurtleBot 4 + Nav2 + YOLO

Dùng map đã lưu để định vị bằng AMCL, chạy tuần tự ba goal bằng Nav2 và nhận diện ảnh camera RGB bằng YOLOv8n. YOLO chỉ quan sát, không điều khiển robot. Bản nộp gồm source và hướng dẫn chạy; model/asset tải riêng, không cần workspace hoặc repository bài 04.

## Cấu trúc

```text
.
├── README.md
├── .gitignore
├── LICENSE
├── LICENSES/Apache-2.0.txt
├── THIRD_PARTY_NOTICES.md
├── scripts/                     # Cài dependency, tải asset, build, môi trường, initial pose
└── src/tb4_yolo_demo/
    ├── package.xml
    ├── setup.py
    ├── setup.cfg
    ├── resource/tb4_yolo_demo    # Ament marker, file rỗng hợp lệ
    ├── tb4_yolo_demo/           # Mission, detector, map/common và spawn người
    ├── launch/                 # Simulation, robot/spawn, navigation, RViz, perception, mission
    ├── config/                 # AMCL/Nav2, goals, mission, detection, objects
    ├── maps/                   # map.yaml và map.pgm
    └── rviz/                   # assignment05.rviz
```

## 1. Cài đặt và build

Yêu cầu **Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress, TurtleBot 4 standard**, namespace rỗng; desktop/OpenGL tương thích Ogre 2, Internet và đủ dung lượng tải PyTorch/mesh. Cài nền theo [ROS Humble](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html) và [TurtleBot 4 simulator](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html), gồm nguồn apt tương ứng.

Mở terminal tại **root bản clone** (nơi có `src/` và `scripts/`), chạy:

```bash
sudo apt update
xargs -r -a scripts/apt-packages.txt sudo apt install -y
source /opt/ros/humble/setup.bash
bash scripts/setup_dependencies.sh
.venv/bin/python scripts/download_model.py
.venv/bin/python scripts/download_assets.py
bash scripts/build.sh
source scripts/env.sh
```

- `apt-packages.txt`: package ROS, hệ thống và công cụ tải/giải nén cần thiết; không cài ROS/Gazebo từ đầu.
- `setup_dependencies.sh`: tạo `.venv` mới bằng `/usr/bin/python3` 3.10 với `--system-site-packages`, cài `requirements-yolo.txt`, gọi `check_environment.py` để kiểm tra import, cv_bridge/NumPy round-trip và CUDA tensor khi có GPU.
- Dependency pip trực tiếp: NumPy 1.26.4, OpenCV 4.10.0.84, Ultralytics 8.3.40, torch 2.5.1, torchvision 0.20.1, cffi 1.17.1. Đây chưa phải lock mọi dependency chuyển tiếp/apt/CUDA. Không nâng NumPy lên 2 hoặc pip sửa Python hệ thống.
- `download_model.py`: tải `models/yolov8n.pt` từ Ultralytics assets v8.3.0. `download_assets.py`: tải Standing person v3 vào `assets/standing_person/`, kiểm tra license và đường dẫn giải nén.
- `build.sh`: gọi `.venv/bin/python /usr/bin/colcon build --symlink-install --packages-select tb4_yolo_demo`, cài ba executable `mission`, `yolo_detector`, `spawn_objects` và toàn bộ launch/config/maps/RViz. Shebang executable phải trỏ tới venv của bản clone đang build.

**Sau khi clone hoặc di chuyển thư mục, tạo lại venv và build/install tại vị trí mới.** Không chép `.venv/`, `build/` hoặc `install/` từ máy khác. Thư mục source không cần mang tên cụ thể.

Mỗi terminal chạy demo phải mở tại root bản clone và dùng:

```bash
source scripts/env.sh
```

Script nạp `/opt/ros/humble/setup.bash` và `install/setup.bash`, đặt Fast DDS UDP profile tới `scripts/fastdds_udp.xml`, cache YOLO tới `.cache/ultralytics`, ROS log tới `logs/`, rồi tạo thư mục log. Nó không activate venv hoặc khởi chạy node. Dùng Fast DDS và cùng `ROS_DOMAIN_ID` cho mọi terminal; profile UDP không áp dụng cho DDS implementation khác.

## 2. Depot và map

Mặc định simulation dùng `worlds/depot.sdf` của `turtlebot4_ignition_bringup` đã cài. World giữ URI Fuel gốc; Gazebo tự tải/cache model còn thiếu. Không cần cache của người học. Lần đầu cần mạng và có thể tải lâu.

Map đi kèm dùng **Depot v6**. URI upstream không khóa version; để khớp đúng version hoặc dùng offline sau khi tải, chuẩn bị override:

```bash
mkdir -p assets/depot_v6
curl --fail --location --retry 3 \
  'https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot/6/Depot.zip' \
  -o assets/depot-v6.zip
unzip -n assets/depot-v6.zip -d assets/depot_v6
test -f assets/depot_v6/model.sdf
```

Khi launch, thêm `depot_asset:="$PWD/assets/depot_v6"`. Chỉ nhánh override mới tạo `artifacts/depot.sdf`; world đã cài trong `/opt/ros` được giữ nguyên. Không thay world khác khi dùng map này.

Map: 753×544 pixel, 0.05 m/pixel, origin `[-15.1, -14.7, 0]`; `map.yaml` dùng `image: map.pgm`. SHA-256:

```text
map.pgm   cbc66a95d617ebcc0a37da61bea893744a74729590ebe87c00c740cd64ae13f4
map.yaml  a63f23e54b5a803d737a593a32aacea25b39908daa3a0de40f343731bde15c43
```

## 3. Simulation, localization và người 3D

Mỗi khối launch dưới dùng terminal riêng, đã source môi trường. Chỉ chạy một simulator và một Nav2.

Terminal 1:

```bash
ros2 launch tb4_yolo_demo simulation.launch.py
```

Hoặc dùng Depot v6 đã tải ở trên, thay lệnh đó bằng:

```bash
ros2 launch tb4_yolo_demo simulation.launch.py depot_asset:="$PWD/assets/depot_v6"
```

Robot/dock spawn tại vị trí mặc định; robot description dùng Ogre 2 cho camera. Máy NVIDIA hybrid có thể cần đặt `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia` trước lệnh simulation/RViz; không bắt buộc trên máy khác, không thay driver/PRIME toàn hệ thống. GPU render độc lập với CUDA inference.

Terminal 2:

```bash
ros2 launch tb4_yolo_demo navigation.launch.py
```

Terminal 3:

```bash
ros2 launch tb4_yolo_demo rviz.launch.py
```

RViz dùng Fixed Frame `map`, hiển thị map/robot/scan/path, camera raw và YOLO. Kiểm tra `/clock` có một publisher, `/amcl` và `/bt_navigator` active:

```bash
ros2 topic info /clock
ros2 lifecycle get /amcl
ros2 lifecycle get /bt_navigator
```

Đặt **2D Pose Estimate** đúng vị trí/hướng, so scan với tường/kệ trên map trước mission. Với lần spawn mặc định mới đã đối chiếu xuất phát gần `(0,0,0)`, có thể dùng:

```bash
.venv/bin/python scripts/initial_pose.py --x 0 --y 0 --yaw 0
```

Không dùng pose zero sau khi robot đã di chuyển. Không chạy SLAM cùng AMCL. Mission không tự xác nhận initial estimate đúng.

Spawn người một lần mỗi simulator:

```bash
ros2 run tb4_yolo_demo spawn_objects \
  --asset-dir "$PWD/assets/standing_person" \
  --config "$PWD/src/tb4_yolo_demo/config/objects.yaml"
```

Người là entity Gazebo tĩnh, có mesh/texture/collision. Pose trong `objects.yaml` thuộc hệ world Gazebo; kiểm tra so với map và camera, giữ ngoài hành lang dự kiến. Không thay tường/kệ đã map hoặc spawn nhiều bản trùng tên.

## 4. YOLO

Terminal 4:

```bash
ros2 launch tb4_yolo_demo perception.launch.py weights:="$PWD/models/yolov8n.pt"
```

Thêm `device:=cpu` để ép CPU; `auto` thử CUDA và chuyển CPU khi không sử dụng được. Camera mặc định `/oakd/rgb/preview/image_raw`; nếu khác, truyền `image_topic:=...`. Quan sát `/yolo/annotated_image` trong RViz với Reliability **Best Effort** và JSON `/yolo/detections`:

```bash
ros2 topic echo /yolo/detections
```

Config mặc định: confidence 0.40, imgsz 640, tối đa 3 inference/s, hai CPU thread. Worker chỉ giữ frame mới nhất; annotated Image giữ header input. YOLOv8n COCO có 80 lớp, gồm person; tường/kệ/carton depot không đảm bảo được nhận diện. Kiểm tra người thật trong field of view trước khi thay threshold.

## 5. Chạy ba goal

Các goal đã nằm trong `config/goals.yaml`, thuộc frame `map`, yaw tính bằng radian. Mission kiểm tra map clearance, readiness/localization, undock nếu còn dock và gọi planner trước mỗi goal. Chỉ bắt đầu sau khi kiểm tra localization, camera và world; không teleop/goal tay/reset pose trong mission.

Terminal 5:

```bash
ros2 launch tb4_yolo_demo mission.launch.py localization_confirmed:=true
```

Node chờ Goal 1 **SUCCEEDED=4** rồi mới gửi Goal 2 và Goal 3. Rejected/aborted/canceled/timeout/lỗi localization làm dừng chuỗi. `max_goals:=1` chỉ dành cho thử một goal; mặc định chạy hết ba goal. Muốn dùng YAML khác, thêm `goals:="$PWD/my_goals.yaml"` với `frame_id: map` và danh sách `name, x, y, yaw` hợp lệ.

Kết quả mới được tạo tại `evidence/runtime/mission_*.json`. Đọc `state`, `completed_goals` và từng `goals[*].action_status`; action accepted hoặc log launch kết thúc không đủ chứng minh thành công. Ba SUCCEEDED không tự chứng minh toàn trajectory không va chạm. Ctrl+C yêu cầu cancel và lưu trạng thái; nếu log không xác nhận cancel, kiểm tra robot đã dừng.

## 6. Output và xử lý lỗi

Repository không chứa sẵn `evidence/`, logs, model, asset, cache hoặc kết quả build. Các chương trình tự tạo output khi cần; dữ liệu này bị ignore. Setup/tải ghi metadata môi trường và nguồn/hash/license vào `evidence/`. Mission tạo JSON như trên; service `/yolo_detector/save_evidence` có thể tạo raw/annotated/JSON mới mà không cần ảnh mẫu đầu vào. Không có bước runtime đọc evidence lịch sử.

- Thiếu executable/import: build lại bằng script và source overlay; kiểm tra shebang venv.
- Lỗi NumPy/cv_bridge ABI: dùng system Python 3.10, venv `--system-site-packages` và dependency đã pin.
- Không có camera: kiểm tra bridge, topic bằng `ros2 topic list -t`, QoS Best Effort và hỗ trợ Ogre 2/OpenGL.
- Thiếu weights/person: chạy hai script tải từ root; kiểm tra `models/yolov8n.pt` và `assets/standing_person/model.sdf`.
- Action/service timeout: source cùng env/DDS/domain ở tất cả terminal; xác định action cũ đã dừng trước khi gửi thêm.
- Scan lệch map/TF cũ: kiểm tra initial pose, sim time và Depot v6; giữ tolerance cấu hình, không tăng để che sai lệch.
- GPU không phù hợp: dùng `device:=cpu` hoặc giảm `image_size`/`inference_rate`; CPU-only đầy đủ cần được kiểm tra trên máy nhận.

Sau thiết lập trên máy mới, phải kiểm tra trực tiếp rendering, scan/map, detection và đủ ba action result. Build thành công không thay thế demo đầy đủ. Dependency chuyển tiếp và URI Depot upstream có thể thay đổi; override v6 giúp giữ hình học map tương ứng.

## 7. Nguồn và giấy phép

Mã dự án: [AGPL-3.0-or-later](LICENSE). Launch Clearpath và YAML sao chép giữ [Apache-2.0](LICENSES/Apache-2.0.txt); xem bảng nguồn/thay đổi trong [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

| Tài nguyên | Nguồn, version và attribution |
|---|---|
| Map | Map Assignment 04 do chủ workspace cung cấp; PGM/YAML được giữ nguyên, không cần project cũ |
| Depot | [OpenRobotics Fuel](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot), v6 cho map; Rafi Abdullah / Louise Poubel, CC BY 4.0 |
| Standing person | [OpenRobotics Fuel](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Standing%20person), v3, tạo bằng MakeHuman, CC0 |
| YOLOv8n | [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/), weights [assets v8.3.0](https://github.com/ultralytics/assets/releases/tag/v8.3.0), Ultralytics AGPL-3.0 |

Model/asset không được phân phối trong repository; giữ attribution khi dùng lại hình học/hình ảnh của chúng.
