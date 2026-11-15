import json
import math
import time

from drone_control.policy import forward_speed
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String
from std_srvs.srv import Trigger


class Controller(Node):
    def __init__(self):
        super().__init__('semantic_controller')
        defaults = {'takeoff_height': 1.1, 'cruise_speed': 0.25,
                    'person_distance': 2.0, 'car_distance': 1.1,
                    'stop_margin': 0.10, 'perception_timeout': 1.0,
                    'max_travel': 20.0}
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        self.p = {key: self.get_parameter(key).value for key in defaults}
        if any(not math.isfinite(value) or value <= 0 for value in self.p.values()):
            raise ValueError('All controller parameters must be positive')
        self.odom = self.origin = self.scene = None
        self.odom_received = 0.0
        self.odom_stamp = 0.0
        self.state = ''
        self.latched = None
        self.airborne = False
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status = self.create_publisher(String, '/semantic/status', 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.create_subscription(String, '/semantic/detections', self.on_scene, 10)
        self.create_service(Trigger, '/semantic/reset', self.reset)
        self.create_timer(0.05, self.tick)

    def on_odom(self, msg):
        """Record initial odometry; takeoff height is relative to spawn height."""
        self.odom = msg.pose.pose
        self.odom_received = time.monotonic()
        self.odom_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.origin is None:
            self.origin = self.odom.position

    def on_scene(self, msg):
        """Reject malformed perception packets by invalidating the last frame."""
        try:
            scene = json.loads(msg.data)
            if not math.isfinite(scene['stamp']) or not isinstance(scene['objects'], list):
                raise ValueError('Invalid perception packet')
            obstacle = scene['obstacle_m']
            if obstacle is not None and (not math.isfinite(obstacle) or obstacle < 0):
                raise ValueError('Invalid obstacle depth')
            for obj in scene['objects']:
                if obj['class'] not in ('person', 'car') or not isinstance(obj['in_path'], bool):
                    raise ValueError('Invalid class or route flag')
                distance = obj['distance_m']
                if distance is not None and (not math.isfinite(distance) or distance < 0):
                    raise ValueError('Invalid object depth')
            self.scene = scene
        except (ValueError, KeyError, TypeError):
            self.scene = None

    def reset(self, request, response):
        """Release the stop latch; an obstacle still present stops it again."""
        self.latched = None
        response.success = True
        response.message = 'Stop reset; fresh sensors and clear route are still required.'
        return response

    def tick(self):
        """Hold on missing data; take off before allowing forward movement."""
        cmd = Twist()
        state = 'WAIT_ODOMETRY'
        now = self.get_clock().now().nanoseconds * 1e-9
        odom_age = now - self.odom_stamp
        if (self.odom is not None and time.monotonic() - self.odom_received < 0.5
                and 0 <= odom_age < 0.5):
            error = self.origin.z + self.p['takeoff_height'] - self.odom.position.z
            cmd.linear.z = max(-0.25, min(0.35, error * 0.8))
            if abs(error) < 0.08:
                self.airborne = True
            state = 'TAKEOFF'
            if self.airborne:
                state = 'WAIT_PERCEPTION'
                if self.scene is not None:
                    age = now - self.scene['stamp']
                    if 0 <= age <= self.p['perception_timeout']:
                        velocity, state = forward_speed(
                            self.scene['objects'], self.scene['obstacle_m'], age,
                            self.p['cruise_speed'],
                            {'person': self.p['person_distance'], 'car': self.p['car_distance']},
                            self.p['stop_margin'])
                        if abs(error) > 0.15:
                            velocity, state = 0.0, 'HOLD_ALTITUDE'
                        if state.startswith('STOP_'):
                            self.latched = state
                        travel = math.hypot(self.odom.position.x - self.origin.x,
                                            self.odom.position.y - self.origin.y)
                        if travel >= self.p['max_travel']:
                            self.latched = 'STOP_MAX_TRAVEL'
                        if self.latched is None:
                            cmd.linear.x = velocity
                if self.latched:
                    state = self.latched
        self.pub.publish(cmd)
        report = {'state': state, 'velocity_x': cmd.linear.x, 'velocity_z': cmd.linear.z,
                  'stamp': now, 'perception': self.scene}
        self.status.publish(String(data=json.dumps(report)))
        if state != self.state:
            self.get_logger().info(f'{self.state or "START"} -> {state}')
            self.state = state


def main(args=None):
    """Run controller and explicitly zero velocity on normal shutdown."""
    rclpy.init(args=args)
    node = Controller()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.pub.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()
