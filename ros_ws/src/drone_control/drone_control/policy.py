"""Pure depth and class-dependent stopping policy, independent of ROS/YOLO."""
import math

import numpy as np


def depth_distance(depth, bbox, minimum_pixels=12):
    """Estimate conservative foreground depth in the central half of a box."""
    h, w = depth.shape
    x1, y1, x2, y2 = bbox
    dx, dy = (x2 - x1) * 0.25, (y2 - y1) * 0.25
    x1, x2 = max(0, int(x1 + dx)), min(w, int(x2 - dx))
    y1, y2 = max(0, int(y1 + dy)), min(h, int(y2 - dy))
    if x2 <= x1 or y2 <= y1:
        return None
    roi = depth[y1:y2, x1:x2]
    valid = roi[np.isfinite(roi) & (roi > 0.15) & (roi < 10.0)]
    if valid.size < minimum_pixels:
        return None
    # Camera pitched down 0.3 rad; allow for its offset from the drone front.
    return max(0.0, float(np.percentile(valid, 20)) * math.cos(0.3) - 0.05)


def forward_speed(objects, obstacle, age, speed, thresholds, margin):
    """Return speed and reason; apply the most restrictive object on the route."""
    command, reason = speed, 'CRUISE'
    for obj in objects:
        label = obj['class']
        if label not in thresholds or not obj['in_path']:
            continue
        distance = obj['distance_m']
        if distance is None or not math.isfinite(distance):
            return 0.0, 'WAIT_OBJECT_DEPTH'
        remaining = distance - thresholds[label] - margin - speed * age
        candidate = min(speed, max(0.0, remaining * 0.6))
        if candidate < command:
            command, reason = candidate, f'APPROACH_{label}'
        if remaining <= 0.03:
            return 0.0, f'STOP_{label}'
    if obstacle is None or not math.isfinite(obstacle):
        return 0.0, 'WAIT_DEPTH'
    if obstacle <= 0.65 + speed * age:
        return 0.0, 'STOP_OBSTACLE'
    return command, reason
