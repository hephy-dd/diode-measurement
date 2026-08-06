from queue import Queue
from threading import Event

from diode_measurement.actors.tcu import TCUActor
from diode_measurement.drivers.ers.ac3 import AC3Adapter


def test_tcu_actor(res):
    res.buffer = ["I0"]

    tcu = AC3Adapter(res)
    event_queue = Queue()
    abort_event = Event()

    actor = TCUActor(tcu, event_queue, abort_event)
    actor.start()
    try:
        assert actor.is_within_setpoint() == True
    finally:
        actor.stop(timeout=1.0)
