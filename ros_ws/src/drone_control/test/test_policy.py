"""Test actual semantic differences, depth failures, and conflicting obstacles."""
from drone_control.policy import depth_distance, forward_speed
import numpy as np
import pytest


def decide(objects, obstacle=5.0, age=0.0):
    return forward_speed(objects, obstacle, age, 0.25,
                         {'person': 2.0, 'car': 1.0}, 0.1)


def detected(label, distance, in_path=True):
    return {'class': label, 'distance_m': distance, 'in_path': in_path}


def test_same_distance_different_class():
    assert decide([detected('person', 1.8)]) == (0.0, 'STOP_person')
    assert decide([detected('car', 1.8)])[0] > 0


def test_car_stops_at_one_meter():
    assert decide([detected('car', 1.0)]) == (0.0, 'STOP_car')


def test_most_restrictive_object_wins():
    assert decide([detected('car', 4.0), detected('person', 2.0)])[0] == 0
    assert decide([detected('person', 2.0), detected('car', 4.0)])[0] == 0


def test_invalid_depth_and_off_route():
    assert decide([detected('person', None)]) == (0.0, 'WAIT_OBJECT_DEPTH')
    assert decide([detected('person', 0.8, False)])[0] > 0
    assert decide([], obstacle=None) == (0.0, 'WAIT_DEPTH')
    assert decide([], obstacle=0.4) == (0.0, 'STOP_OBSTACLE')


def test_inference_latency_reduces_speed():
    obj = [detected('person', 2.5)]
    assert decide(obj, age=0.8)[0] < decide(obj, age=0.0)[0]


def test_depth_rejects_bad_pixels_and_background():
    depth = np.full((40, 40), np.nan, dtype=np.float32)
    assert depth_distance(depth, [0, 0, 40, 40]) is None
    depth[10:30, 10:30] = 2.0
    depth[10, 10] = np.inf
    depth[11, 11] = 0.0
    assert depth_distance(depth, [0, 0, 40, 40]) == pytest.approx(1.86067, abs=0.001)
    assert depth_distance(depth, [-100, -100, -50, -50]) is None
