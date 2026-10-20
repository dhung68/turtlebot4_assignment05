# Third-party notices

Original Assignment 05 code is licensed under AGPL-3.0-or-later; see [LICENSE](LICENSE).
The following upstream files retain their Apache-2.0 license. The complete text is
included in [LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt).

| Included file | Upstream | Changes |
|---|---|---|
| `src/tb4_yolo_demo/launch/turtlebot4_spawn.launch.py` | [turtlebot4_simulator 1.0.3](https://github.com/turtlebot/turtlebot4_simulator/tree/1.0.3), `turtlebot4_ignition_bringup/launch/turtlebot4_spawn.launch.py`; Copyright 2021 Clearpath Robotics, Inc.; author Roni Kreinin | Route robot description to this package's Ogre 2 wrapper; add modification notice. Original header retained. |
| `src/tb4_yolo_demo/config/nav2.yaml` | [turtlebot4 1.0.5](https://github.com/turtlebot/turtlebot4/tree/1.0.5), `turtlebot4_navigation/config/nav2.yaml` | Attribution comments and final newline; parameters unchanged. |
| `src/tb4_yolo_demo/config/localization.yaml` | [turtlebot4 1.0.5](https://github.com/turtlebot/turtlebot4/tree/1.0.5), `turtlebot4_navigation/config/localization.yaml` | Attribution comments; parameters unchanged. |

Sources and package versions were compared with the installed ROS Humble packages.
The two YAML files contained no file-level copyright headers in those packages.
The launch copyright and author attribution are preserved. Other launch files wrap
installed packages; the upstream world, xacro, plugins and meshes are dependencies
and are not redistributed here.

Downloaded assets and weights are excluded:

| Asset | Source / version | Attribution / license |
|---|---|---|
| Depot | [OpenRobotics Fuel](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Depot), version 6 for the supplied map | Rafi Abdullah / Louise Poubel; Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)). Geometry is not modified. |
| Standing person | [OpenRobotics Fuel](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Standing%20person), version 3, made with MakeHuman | Creative Commons Zero v1.0 Universal ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)). Runtime wrapper makes the model static and resolves mesh paths locally. |
| YOLOv8n | [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8/), weights from [assets v8.3.0](https://github.com/ultralytics/assets/releases/tag/v8.3.0) | Ultralytics AGPL-3.0; weights are downloaded separately. |
| Map | Assignment 04 map supplied by the workspace owner | The PGM and YAML are included unchanged; no Assignment 04 repository or directory is needed. |

See [README.md](README.md) for setup and download commands. Download scripts record
source/license/checksum metadata in the generated, ignored `evidence/` directory.
