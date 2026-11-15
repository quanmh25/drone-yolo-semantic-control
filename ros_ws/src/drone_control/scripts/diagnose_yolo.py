#!/usr/bin/env python3
"""Capture a live RGB frame and report unfiltered YOLO labels for diagnosis."""
import argparse
import json
from pathlib import Path
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from ultralytics import YOLO


def main():
    """Compare raw model predictions with the classes accepted by perception."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', required=True)
    parser.add_argument('--output', default='/tmp/drone-yolo-diagnosis.png')
    args = parser.parse_args()
    if not Path(args.weights).is_file():
        parser.error('The weights file does not exist')
    rclpy.init()
    node = rclpy.create_node('diagnose_yolo')
    frames = []
    subscription = node.create_subscription(
        Image, '/front_rgbd/image', frames.append, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + 10.0
        while not frames and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if not frames:
            raise RuntimeError('No RGB frame within 10 seconds; keep the demo running '
                               'and check ROS_DOMAIN_ID and the camera topic.')
        frame = CvBridge().imgmsg_to_cv2(frames[-1], desired_encoding='bgr8')
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()
    result = YOLO(args.weights).predict(frame, conf=0.05, device='cpu', verbose=False)[0]
    detections = []
    for box in result.boxes:
        label = result.names[int(box.cls.item())]
        confidence = float(box.conf.item())
        detections.append({
            'class': label, 'confidence': round(confidence, 4),
            'accepted_at_default_settings': label in ('person', 'car') and confidence >= 0.35,
            'bbox': box.xyxy[0].cpu().tolist(),
        })
    if not cv2.imwrite(args.output, result.plot()):
        raise RuntimeError(f'Could not save diagnostic image: {args.output}')
    print(json.dumps({'image': args.output, 'diagnostic_confidence': 0.05,
                      'detections': detections}, indent=2))


if __name__ == '__main__':
    main()
