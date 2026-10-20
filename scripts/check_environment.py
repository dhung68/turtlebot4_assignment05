import json
import platform
import sys
from pathlib import Path

import cv2
import numpy as np
from cv_bridge import CvBridge
import rclpy
import torch
import torchvision
import ultralytics

bridge = CvBridge()
image = np.zeros((24,32,3),dtype=np.uint8)
assert np.array_equal(image, bridge.imgmsg_to_cv2(bridge.cv2_to_imgmsg(image,'bgr8'),'bgr8'))
data = {'python':sys.executable, 'version':platform.python_version(),'numpy':np.__version__,
        'opencv':cv2.__version__,'torch':torch.__version__,'torchvision':torchvision.__version__,
        'ultralytics':ultralytics.__version__,'cv_bridge_roundtrip':True,'cuda_available':torch.cuda.is_available()}
if data['cuda_available']:
    x = torch.ones((64,64),device='cuda'); y = x@x; torch.cuda.synchronize()
    data.update(gpu=torch.cuda.get_device_name(), cuda_tensor_test=bool(y[0,0].item()==64),
                vram_total_bytes=torch.cuda.get_device_properties(0).total_memory)
Path('evidence').mkdir(exist_ok=True)
Path('evidence/python_environment.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data,indent=2))
