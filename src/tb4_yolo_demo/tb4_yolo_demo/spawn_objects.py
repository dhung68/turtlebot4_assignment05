import argparse
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asset-dir', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--world', default='depot')
    args = parser.parse_args()
    asset = Path(args.asset_dir).resolve()
    source = asset/'model.sdf'
    if not source.is_file():
        raise FileNotFoundError('Download Standing person first: scripts/download_assets.py')
    config = yaml.safe_load(Path(args.config).read_text())
    for item in config['objects']:
        tree = ET.parse(source)
        model = tree.getroot().find('model')
        model.set('name', item['name'])
        old_static = model.find('static')
        if old_static is not None:
            model.remove(old_static)
        ET.SubElement(model, 'static').text = 'true'
        for uri in model.findall('.//uri'):
            if uri.text.startswith('model://person_standing/'):
                uri.text = str(asset/uri.text.split('model://person_standing/',1)[1])
        with tempfile.TemporaryDirectory(prefix='tb4_object_') as temp:
            filename = Path(temp)/'person.sdf'
            tree.write(filename, encoding='unicode')
            command = ['ros2','run','ros_gz_sim','create','-world',args.world,'-name',item['name'],
                       '-file',str(filename),'-x',str(item['x']),'-y',str(item['y']),'-z',str(item.get('z',0.)),
                       '-Y',str(item['yaw']),'-allow_renaming','false']
            print('Spawning:', item, flush=True)
            subprocess.run(command, check=True, timeout=30)
    print('Check Gazebo entity names and live camera; spawning alone does not prove detection.')
