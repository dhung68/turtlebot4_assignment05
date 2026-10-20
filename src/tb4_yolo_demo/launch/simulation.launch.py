from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
import xml.etree.ElementTree as ET


def simulation(context):
    upstream = Path(get_package_share_directory('turtlebot4_ignition_bringup'))/'launch'
    local = Path(get_package_share_directory('tb4_yolo_demo'))/'launch'
    source = upstream.parent/'worlds/depot.sdf'
    world = source
    asset = LaunchConfiguration('depot_asset').perform(context).strip()
    if asset:
        cache = Path(asset).expanduser().resolve()
        if not (cache/'model.sdf').is_file():
            raise FileNotFoundError(f'Depot model.sdf missing in depot_asset: {cache}')
        tree = ET.parse(source)
        uri = tree.getroot().find('world/include/uri')
        if uri is None:
            raise RuntimeError(f'Depot include missing in installed world: {source}')
        uri.text = str(cache)
        world = Path('artifacts/depot.sdf').resolve()
        world.parent.mkdir(parents=True, exist_ok=True)
        tree.write(world, encoding='unicode')
    return [
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(upstream/'ignition.launch.py')),
                                 launch_arguments={'world':str(world.with_suffix('')), 'model':'standard'}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(local/'turtlebot4_spawn.launch.py')),
                                 launch_arguments={**{n:LaunchConfiguration(n) for n in ('x','y','yaw')},
                                                   'world':'depot','rviz':'false'}.items()),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('depot_asset', default_value='',
                              description='Optional local Depot directory containing model.sdf; empty uses installed world and Fuel'),
        *[DeclareLaunchArgument(n,default_value='0.0') for n in ('x','y','yaw')],
        OpaqueFunction(function=simulation),
    ])
