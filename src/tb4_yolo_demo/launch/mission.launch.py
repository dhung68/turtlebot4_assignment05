from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package = Path(get_package_share_directory('tb4_yolo_demo'))
    return LaunchDescription([
        DeclareLaunchArgument('goals', default_value=str(package/'config/goals.yaml')),
        DeclareLaunchArgument('map', default_value=str(package/'maps/map.yaml')),
        DeclareLaunchArgument('localization_confirmed', default_value='false'),
        DeclareLaunchArgument('max_goals', default_value='0'),
        DeclareLaunchArgument('results_dir', default_value='evidence/runtime'),
        Node(package='tb4_yolo_demo', executable='mission', output='screen',
             parameters=[str(package/'config/mission.yaml'), {'goals_file':LaunchConfiguration('goals'),
                         'map_file':LaunchConfiguration('map'), 'results_dir':LaunchConfiguration('results_dir'),
                         'localization_confirmed':ParameterValue(LaunchConfiguration('localization_confirmed'),value_type=bool),
                         'max_goals':ParameterValue(LaunchConfiguration('max_goals'),value_type=int)}]),
    ])
