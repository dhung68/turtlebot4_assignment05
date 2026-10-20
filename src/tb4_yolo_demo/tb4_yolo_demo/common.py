import json
import math
import os
from pathlib import Path

import yaml


def load_goals(filename, minimum=3):
    data = yaml.safe_load(Path(filename).read_text())
    if not isinstance(data, dict) or data.get('frame_id') != 'map':
        raise ValueError('Goal frame_id must be map')
    goals = data.get('goals', [])
    if len(goals) < minimum:
        raise ValueError(f'Need at least {minimum} collected goals; got {len(goals)}')
    names = set()
    for goal in goals:
        if not isinstance(goal.get('name'), str) or goal['name'] in names:
            raise ValueError('Goal names must be unique strings')
        names.add(goal['name'])
        for field in ('x', 'y', 'yaw'):
            if isinstance(goal.get(field), bool) or not math.isfinite(float(goal[field])):
                raise ValueError(f'Invalid {field} in {goal}')
            goal[field] = float(goal[field])
    return goals


def yaw_from_quaternion(q):
    norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
    if norm < 1e-9:
        raise ValueError('Zero quaternion')
    x, y, z, w = (v / norm for v in (q.x, q.y, q.z, q.w))
    return math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))


def atomic_json(filename, data):
    path = Path(filename).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False))
    os.replace(temp, path)
