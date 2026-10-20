from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package = Path(get_package_share_directory('tb4_yolo_demo'))
    return LaunchDescription([
        DeclareLaunchArgument('config', default_value=str(package/'config/detection.yaml')),
        DeclareLaunchArgument('weights', default_value='models/yolov8n.pt'),
        DeclareLaunchArgument('device', default_value='auto'),
        DeclareLaunchArgument('image_topic', default_value='/oakd/rgb/preview/image_raw'),
        Node(package='tb4_yolo_demo', executable='yolo_detector', output='screen',
             parameters=[LaunchConfiguration('config'), {'use_sim_time':True,
                         'weights':LaunchConfiguration('weights'), 'device':LaunchConfiguration('device'),
                         'image_topic':LaunchConfiguration('image_topic')}]),
    ])
