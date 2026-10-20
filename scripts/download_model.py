from pathlib import Path
import hashlib
import json
import os
import urllib.request

os.environ.setdefault('YOLO_CONFIG_DIR', str(Path('.cache/ultralytics').resolve()))
from ultralytics import YOLO

path = Path('models/yolov8n.pt')
path.parent.mkdir(exist_ok=True)
if not path.exists():
    url = 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt'
    urllib.request.urlretrieve(url, path.with_suffix('.download'))
    path.with_suffix('.download').replace(path)
model = YOLO(str(path))
metadata = {'model':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'task':model.task,'names':model.names,'source':'https://github.com/ultralytics/assets/releases/tag/v8.3.0'}
Path('evidence').mkdir(exist_ok=True)
Path('evidence/model_classes.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata,indent=2))
