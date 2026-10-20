from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node
import xacro


def robot_description(context):
    source = Path(get_package_share_directory('turtlebot4_description'))/'urdf/standard/turtlebot4.urdf.xacro'
    description = xacro.process_file(str(source), mappings={'gazebo':'ignition','namespace':''}).toxml()
    description = description.replace('<render_engine>ogre</render_engine>', '<render_engine>ogre2</render_engine>')
    return [
        Node(package='robot_state_publisher', executable='robot_state_publisher', output='screen',
             parameters=[{'use_sim_time':True,'robot_description':description}]),
        Node(package='joint_state_publisher', executable='joint_state_publisher', parameters=[{'use_sim_time':True}]),
    ]


def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=robot_description)])
