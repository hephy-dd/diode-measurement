from threading import Event

from diode_measurement.actors.tcu import TCUActor
from diode_measurement.core.events import EventBus
from diode_measurement.drivers.ac3 import AC3


def test_tcu_actor(res):
    res.buffer = ["I0"]

    tcu = AC3(res)
    event_bus = EventBus()
    abort_event = Event()

    actor = TCUActor(tcu, event_bus, abort_event)
    actor.start()
    try:
        assert actor.is_within_setpoint() == True
    finally:
        actor.stop(timeout=1.0)
