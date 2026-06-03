import math

from assassin.systems.detection import (
    Awareness,
    DetectionMeter,
    angle_diff,
    in_vision_cone,
    line_of_sight,
)


def test_angle_diff_wraps():
    assert angle_diff(0.1, -0.1) == 0.2 or abs(angle_diff(0.1, -0.1) - 0.2) < 1e-9
    assert abs(angle_diff(0.0, 2 * math.pi)) < 1e-9
    assert abs(angle_diff(math.pi, -math.pi)) < 1e-9


def test_in_vision_cone_range_and_angle():
    obs = (0.0, 0.0)
    # facing +x, 90 degree cone, range 100
    assert in_vision_cone(obs, 0.0, math.pi / 2, 100, (50, 0))   # straight ahead
    assert not in_vision_cone(obs, 0.0, math.pi / 2, 100, (150, 0))  # too far
    assert not in_vision_cone(obs, 0.0, math.pi / 2, 100, (-50, 0))  # behind
    assert in_vision_cone(obs, 0.0, math.pi / 2, 100, (40, 30))   # within cone edge


def test_line_of_sight_clear_and_blocked():
    # wall column at x == 3
    def blocked(c, r):
        return c == 3

    assert line_of_sight(blocked, (0, 0), (2, 0))      # before the wall
    assert not line_of_sight(blocked, (0, 0), (6, 0))  # straight through wall

    # endpoints are never treated as blockers: a blocker sitting on the start
    # or end tile does not block sight when the path between is clear.
    def blocked_single(c, r):
        return (c, r) == (2, 0)

    assert line_of_sight(blocked_single, (2, 0), (5, 0))  # blocker is the start
    assert line_of_sight(blocked_single, (5, 0), (2, 0))  # blocker is the end


def test_detection_meter_fills_then_alerts_and_latches():
    m = DetectionMeter(fill_rate=2.0, decay_rate=1.0)
    assert m.state is Awareness.UNAWARE
    # fill for 0.6s at intensity 1 -> value 1.2 -> clamped to 1.0 -> ALERT
    m.update(0.6, visible=True, intensity=1.0)
    assert m.state is Awareness.ALERT
    # one frame not visible should NOT immediately clear (latched)
    m.update(0.2, visible=False)
    assert m.state is Awareness.ALERT


def test_detection_meter_decays_and_unlatches_at_zero():
    m = DetectionMeter(fill_rate=2.0, decay_rate=2.0)
    m.update(1.0, visible=True)          # -> alert, value 1.0
    assert m.state is Awareness.ALERT
    m.update(1.0, visible=False)         # decay back to 0
    assert m.value == 0.0
    assert m.state is Awareness.UNAWARE


def test_intensity_scales_fill_rate():
    fast = DetectionMeter(fill_rate=1.0, decay_rate=1.0)
    slow = DetectionMeter(fill_rate=1.0, decay_rate=1.0)
    fast.update(0.3, True, intensity=1.5)
    slow.update(0.3, True, intensity=0.5)
    assert fast.value > slow.value


def test_suspicious_threshold():
    m = DetectionMeter(fill_rate=1.0, decay_rate=1.0)
    m.update(0.5, True)  # value 0.5 -> above suspicious (0.45), below alert
    assert m.state is Awareness.SUSPICIOUS
