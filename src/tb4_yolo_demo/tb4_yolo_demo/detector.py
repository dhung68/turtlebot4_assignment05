from copy import deepcopy
import json
from pathlib import Path
import threading
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from std_srvs.srv import Trigger

from .common import atomic_json


class Detector(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        defaults = {'use_sim_time': True, 'image_topic': '/oakd/rgb/preview/image_raw',
                    'annotated_topic': '/yolo/annotated_image', 'weights': 'models/yolov8n.pt',
                    'confidence': .4, 'image_size': 640, 'inference_rate': 3., 'device': 'auto',
                    'cpu_threads': 2, 'log_period': 5., 'image_timeout': 5., 'evidence_dir': 'evidence/runtime'}
        for key, value in defaults.items():
            if not self.has_parameter(key):
                self.declare_parameter(key, value)
        self.config = {k:self.get_parameter(k).value for k in defaults}
        if self.config['inference_rate'] <= 0 or not 0 < self.config['confidence'] <= 1:
            raise ValueError('inference_rate must be positive and confidence in (0,1]')
        weights = Path(self.config['weights']).expanduser()
        if not weights.is_file():
            raise FileNotFoundError(f'Weights missing: {weights}. Run scripts/download_model.py using .venv/bin/python')
        import torch
        from ultralytics import YOLO
        self.torch = torch
        torch.set_num_threads(self.config['cpu_threads'])
        self.device = self.select_device(self.config['device'])
        self.model = YOLO(str(weights), task='detect')
        if self.model.task != 'detect':
            raise ValueError('Expected a detection model')
        self.get_logger().info(f'Inference device={self.device}; classes={self.model.names}')
        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.latest = None
        self.sequence = 0
        self.snapshot = None
        self.stopping = threading.Event()
        self.started = time.monotonic()
        self.last_received = self.started
        self.last_log = 0.
        self.publisher = self.create_publisher(Image, self.config['annotated_topic'], qos_profile_sensor_data)
        self.detections = self.create_publisher(String, '/yolo/detections', 10)
        self.create_subscription(Image, self.config['image_topic'], self.receive, qos_profile_sensor_data)
        self.create_service(Trigger, '~/save_evidence', self.save_evidence)
        self.create_timer(2., self.watchdog)
        self.worker = threading.Thread(target=self.process, name='yolo_inference', daemon=True)
        self.worker.start()

    def select_device(self, requested):
        torch = self.torch
        if requested == 'cpu':
            return 'cpu'
        candidate = 'cuda:0' if requested == 'auto' else ('cuda:'+requested if requested.isdigit() else requested)
        try:
            if not torch.cuda.is_available():
                raise RuntimeError('torch.cuda.is_available() is false')
            tensor = torch.ones((32,32), device=candidate)
            _ = tensor @ tensor
            torch.cuda.synchronize()
            self.get_logger().info(f'CUDA verified with tensor operation: {torch.cuda.get_device_name(tensor.device)}')
            return candidate
        except Exception as exc:
            self.get_logger().warning(f'CUDA unavailable ({exc}); using CPU')
            return 'cpu'

    def receive(self, msg):
        with self.lock:
            self.latest = msg
            self.sequence += 1
            self.last_received = time.monotonic()

    def watchdog(self):
        if time.monotonic()-self.last_received > self.config['image_timeout']:
            self.get_logger().warning(f"No fresh images on {self.config['image_topic']}; inspect topic, bridge and QoS")

    def process(self):
        processed = -1
        failures = 0
        while not self.stopping.is_set():
            start = time.monotonic()
            with self.lock:
                msg, sequence = self.latest, self.sequence
            if msg is not None and sequence != processed:
                processed = sequence
                try:
                    stamp = msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
                    age = self.get_clock().now().nanoseconds*1e-9-stamp
                    if self.config['use_sim_time'] and (age > self.config['image_timeout'] or age < -.5):
                        self.stopping.wait(.1)
                        continue
                    frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
                    inference_start = time.monotonic()
                    result = self.model.predict(frame, conf=self.config['confidence'], imgsz=self.config['image_size'],
                                                device=self.device, verbose=False, max_det=50)[0]
                    inference_ms = (time.monotonic()-inference_start)*1000
                    annotated = result.plot()
                    output = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
                    output.header = deepcopy(msg.header)
                    self.publisher.publish(output)
                    objects = [{'class_id':int(box.cls.item()), 'class_name':result.names[int(box.cls.item())],
                                'confidence':float(box.conf.item()), 'xyxy':box.xyxy[0].cpu().tolist()}
                               for box in result.boxes]
                    metadata = {'stamp':{'sec':msg.header.stamp.sec,'nanosec':msg.header.stamp.nanosec},
                                'frame_id':msg.header.frame_id, 'source_topic':self.config['image_topic'],
                                'device':self.device,'inference_ms':inference_ms,'input_age_sim_seconds':age,
                                'objects':objects,'weights':self.config['weights'], 'config':self.config}
                    self.detections.publish(String(data=json.dumps(metadata)))
                    with self.lock:
                        self.snapshot = (frame.copy(), annotated.copy(), metadata)
                    if time.monotonic()-self.last_log >= self.config['log_period']:
                        summary = ', '.join(f"{o['class_name']} {o['confidence']:.2f}" for o in objects) or 'no detections'
                        self.get_logger().info(f'{summary}; device={self.device}; inference={inference_ms:.1f} ms; input_age={age:.3f} sim s')
                        self.last_log = time.monotonic()
                    failures = 0
                except Exception as exc:
                    failures += 1
                    if self.device != 'cpu':
                        self.get_logger().error(f'GPU inference failed: {exc}; retrying future frames on CPU')
                        self.device = 'cpu'
                        self.model.to('cpu')
                        self.torch.cuda.empty_cache()
                    elif failures == 1 or failures % 10 == 0:
                        self.get_logger().error(f'Image conversion/inference error ({failures}): {exc}')
            self.stopping.wait(max(0., 1./self.config['inference_rate']-(time.monotonic()-start)))

    def save_evidence(self, request, response):
        with self.lock:
            snapshot = self.snapshot
        if snapshot is None:
            response.success, response.message = False, 'No processed camera image available'
            return response
        frame, annotated, metadata = snapshot
        path = Path(self.config['evidence_dir']).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        stem = path / f"detection_{metadata['stamp']['sec']}_{metadata['stamp']['nanosec']}"
        if not cv2.imwrite(str(stem)+'_raw.png',frame) or not cv2.imwrite(str(stem)+'_annotated.png',annotated):
            response.success, response.message = False, 'Failed writing image'
            return response
        atomic_json(str(stem)+'.json', metadata)
        response.success, response.message = True, str(stem)
        return response

    def close(self):
        self.stopping.set()
        self.worker.join(timeout=15.)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = Detector()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
