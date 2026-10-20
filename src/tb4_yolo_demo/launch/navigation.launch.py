from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    package = Path(get_package_share_directory('tb4_yolo_demo'))
    navigation = Path(get_package_share_directory('turtlebot4_navigation'))
    def include(filename, args):
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(str(navigation/'launch'/filename)), launch_arguments=args.items())
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=str(package/'maps/map.yaml')),
        DeclareLaunchArgument('localization_params', default_value=str(package/'config/localization.yaml')),
        DeclareLaunchArgument('nav2_params', default_value=str(package/'config/nav2.yaml')),
        include('localization.launch.py', {'map':LaunchConfiguration('map'), 'params':LaunchConfiguration('localization_params'), 'use_sim_time':'true'}),
        include('nav2.launch.py', {'params_file':LaunchConfiguration('nav2_params'), 'use_sim_time':'true'}),
    ])
