"""Exercise the flight state machine with ROS messages and a real ROS clock."""
import json

from drone_control.controller import Controller
from nav_msgs.msg import Odometry
import pytest
import rclpy
from std_msgs.msg import String


@pytest.fixture
def controller(monkeypatch):
    """Create an isolated controller without publishing test velocity commands."""
    rclpy.init()
    node = Controller()
    commands = []
    monkeypatch.setattr(node.pub, 'publish', commands.append)
    node.commands = commands
    yield node
    node.destroy_node()
    rclpy.shutdown()


def odom(node, height):
    msg = Odometry()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.pose.pose.position.z = height
    msg.pose.pose.orientation.w = 1.0
    node.on_odom(msg)


def scene(node, label='car', distance=1.8, age=0.0):
    stamp = node.get_clock().now().nanoseconds * 1e-9 - age
    node.on_scene(String(data=json.dumps({
        'stamp': stamp, 'obstacle_m': 5.0,
        'objects': [{'class': label, 'distance_m': distance, 'in_path': True}]})))


def airborne(node):
    odom(node, 0.15)
    odom(node, 1.25)


def test_takeoff_and_wait_for_inference(controller):
    node = controller
    node.tick()
    assert node.commands[-1].linear.x == 0
    odom(node, 0.15)
    node.tick()
    assert node.state == 'TAKEOFF'
    assert node.commands[-1].linear.z > 0
    odom(node, 1.25)
    node.tick()
    assert node.state == 'WAIT_PERCEPTION'
    assert node.commands[-1].linear.x == 0


def test_class_changes_command_and_stop_latches(controller):
    node = controller
    airborne(node)
    scene(node, 'car', 1.8)
    node.tick()
    assert node.commands[-1].linear.x > 0
    scene(node, 'person', 1.8)
    node.tick()
    assert node.state == 'STOP_person'
    assert node.commands[-1].linear.x == 0
    scene(node, 'car', 5.0)
    node.tick()
    assert node.commands[-1].linear.x == 0
    assert node.state == 'STOP_person'


def test_stale_perception_and_missing_odom_stop(controller):
    node = controller
    airborne(node)
    scene(node, age=3.0)
    node.tick()
    assert node.commands[-1].linear.x == 0
    scene(node)
    node.tick()
    assert node.commands[-1].linear.x > 0
    node.odom_received = 0.0
    node.tick()
    assert node.state == 'WAIT_ODOMETRY'
    assert node.commands[-1].linear.x == 0
    assert node.commands[-1].linear.z == 0


def test_bad_packet_invalidates_previous_frame(controller):
    node = controller
    airborne(node)
    scene(node)
    node.on_scene(String(data='{"stamp": 123, "objects": []}'))
    node.tick()
    assert node.commands[-1].linear.x == 0
    assert node.scene is None
