import pytest

from diode_measurement.core import utils


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


@pytest.fixture
def clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(utils.time, "monotonic", clock)
    return clock


def test_negative_interval():
    with pytest.raises(ValueError):
        utils.IntervalTimer(-1)


def test_expiration(clock):
    t = utils.IntervalTimer(10)

    assert not t

    clock.advance(10)
    assert t  # __bool__


def test_reset(clock):
    t = utils.IntervalTimer(5)

    clock.advance(6)
    assert t

    t.reset()
    assert not t


def test_remaining(clock):
    t = utils.IntervalTimer(10)

    clock.advance(3)
    assert t.remaining() == 7

    clock.advance(10)
    assert t.remaining() == 0


def test_zero_interval(clock):
    t = utils.IntervalTimer(0)
    assert t
    assert t.remaining() == 0
