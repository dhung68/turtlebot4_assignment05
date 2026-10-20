from glob import glob
from pathlib import Path
from setuptools import setup

setup(
    name='tb4_yolo_demo', version='0.1.0',
    packages=['tb4_yolo_demo'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/tb4_yolo_demo']),
        ('share/tb4_yolo_demo', ['package.xml']),
        *[(f'share/tb4_yolo_demo/{folder}', [p for p in glob(f'{folder}/*') if Path(p).is_file()])
          for folder in ('launch', 'config', 'maps', 'rviz')],
    ],
    install_requires=['setuptools', 'PyYAML'], zip_safe=True,
    maintainer='Assignment 05 student', maintainer_email='student@example.com',
    description='TurtleBot 4 sequential Nav2 mission and camera YOLO detection',
    license='AGPL-3.0-or-later',
    entry_points={'console_scripts': [
        'mission = tb4_yolo_demo.mission:main',
        'yolo_detector = tb4_yolo_demo.detector:main',
        'spawn_objects = tb4_yolo_demo.spawn_objects:main',
    ]},
)
