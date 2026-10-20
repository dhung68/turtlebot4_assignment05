from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = Path(get_package_share_directory('tb4_yolo_demo'))/'rviz/assignment05.rviz'
    return LaunchDescription([Node(package='rviz2', executable='rviz2', arguments=['-d',str(config)], parameters=[{'use_sim_time':True}], output='screen')])
