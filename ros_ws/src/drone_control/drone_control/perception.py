"""Synchronized RGB-D YOLO perception; publish real detections and debug images."""
import json
import math
from pathlib import Path

import cv2
from cv_bridge import CvBridge
from drone_control.policy import depth_distance
from message_filters import ApproximateTimeSynchronizer, Subscriber
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


class Perception(Node):
    """Run inference separately from the velocity-control process."""

    def __init__(self):
        super().__init__('semantic_perception')
        for key, value in {'weights': '', 'confidence': 0.35,
                           'inference_hz': 5.0, 'device': 'cpu'}.items():
            self.declare_parameter(key, value)
        rate = self.get_parameter('inference_hz').value
        confidence = self.get_parameter('confidence').value
        if not math.isfinite(rate) or rate <= 0:
            raise ValueError('inference_hz must be finite and positive')
        if not math.isfinite(confidence) or not 0 < confidence <= 1:
            raise ValueError('confidence must be in (0, 1]')
        weights = Path(self.get_parameter('weights').value).expanduser()
        if not weights.is_file():
            raise RuntimeError('Set weights:=/absolute/path/to/yolov8n.pt; '
                               'automatic downloads during flight are disabled.')
        from ultralytics import YOLO
        self.model = YOLO(str(weights))
        self.bridge = CvBridge()
        self.latest = None
        self.pub = self.create_publisher(String, '/semantic/detections', 10)
        self.image_pub = self.create_publisher(Image, '/semantic/annotated', 1)
        self.rgb_sub = Subscriber(self, Image, '/front_rgbd/image',
                                  qos_profile=qos_profile_sensor_data)
        self.depth_sub = Subscriber(self, Image, '/front_rgbd/depth_image',
                                    qos_profile=qos_profile_sensor_data)
        self.sync = ApproximateTimeSynchronizer(
            [self.rgb_sub, self.depth_sub], queue_size=5, slop=0.06)
        self.sync.registerCallback(self.receive)
        self.create_timer(1.0 / rate, self.infer)

    def receive(self, rgb, depth):
        """Keep the newest synchronized pair instead of queuing old inference."""
        self.latest = (rgb, depth)

    def infer(self):
        """Publish original image timestamp so stale inference cannot command flight."""
        if self.latest is None:
            return
        rgb, depth_msg = self.latest
        self.latest = None
        try:
            frame = self.bridge.imgmsg_to_cv2(rgb, desired_encoding='bgr8')
            depth = self.bridge.imgmsg_to_cv2(depth_msg).astype(np.float32)
            if depth_msg.encoding == '16UC1':
                depth *= 0.001
            elif depth_msg.encoding != '32FC1':
                raise ValueError(f'Unsupported depth encoding: {depth_msg.encoding}')
            if depth.shape != frame.shape[:2]:
                raise ValueError('RGB and depth must be pixel aligned with equal size')
            result = self.model.predict(
                frame, conf=self.get_parameter('confidence').value,
                device=self.get_parameter('device').value, verbose=False)[0]
            h, w = depth.shape
            objects = []
            for box in result.boxes:
                label = result.names[int(box.cls.item())]
                if label not in ('person', 'car'):
                    continue
                bbox = box.xyxy[0].cpu().tolist()
                distance = depth_distance(depth, bbox)
                # Image corridor approximates the straight flight route.
                in_path = bbox[0] < 0.62 * w and bbox[2] > 0.38 * w
                objects.append({'class': label, 'confidence': float(box.conf.item()),
                                'bbox': bbox, 'distance_m': distance, 'in_path': in_path})
                x, y = int(bbox[0]), max(20, int(bbox[1]) - 8)
                text = (f'{label}: {distance:.2f} m' if distance is not None
                        else f'{label}: no depth')
                cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 255), 1)
                cv2.rectangle(frame, (x, int(bbox[1])),
                              (int(bbox[2]), int(bbox[3])), (0, 255, 255), 2)
            # Upper central region avoids most ground pixels from the tilted camera.
            obstacle = depth_distance(depth, (0.35*w, 0.1*h, 0.65*w, 0.6*h))
            stamp = rgb.header.stamp.sec + rgb.header.stamp.nanosec * 1e-9
            self.pub.publish(String(data=json.dumps({
                'stamp': stamp, 'objects': objects, 'obstacle_m': obstacle}, allow_nan=False)))
            annotated = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            annotated.header = rgb.header
            self.image_pub.publish(annotated)
        except Exception as exc:
            self.get_logger().error(f'Perception failed; controller will hold: {exc}')


def main(args=None):
    """Run perception with an explicitly supplied local YOLO model."""
    rclpy.init(args=args)
    node = None
    try:
        node = Perception()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()
