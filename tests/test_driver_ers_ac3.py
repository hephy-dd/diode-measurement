import math

import pytest

from diode_measurement.core.events import (
    ChangeDewpointControl,
    ChangeTargetTemperature,
)
from diode_measurement.drivers.ers.ac3 import AC3Adapter


def test_ac3_adapter(res):
    d = AC3Adapter(res)

    res.buffer = ["ERS AC3 Thermal Chuck\r"]
    assert d.identify() == "ERS AC3 Thermal Chuck"
    assert res.buffer == ["RI"]

    res.buffer = []
    assert d.reset() is None
    assert res.buffer == []

    res.buffer = []
    assert d.clear() is None
    assert res.buffer == []

    res.buffer = ["E0"]
    assert d.next_error() is None
    assert res.buffer == ["RE"]

    # temperature
    res.buffer = ["C0214"]
    assert d.get_temperature() == 21.4
    assert res.buffer == ["RC"]

    # humidity is not supported
    assert math.isnan(d.get_humidity())

    # setpoint is always enabled
    assert d.is_setpoint_enabled() is True

    res.buffer = []
    assert d.set_setpoint_enabled(True) is None
    assert res.buffer == []

    # target temperature
    res.buffer = ["T+0214"]
    assert d.set_target_temperature(21.4) is None
    assert res.buffer == ["ST+0214"]

    res.buffer = ["T-0050"]
    assert d.set_target_temperature(-5.0) is None
    assert res.buffer == ["ST-0050"]

    # setpoint status
    res.buffer = ["I0"]
    assert d.is_within_setpoint() is True
    assert res.buffer == ["RI"]

    res.buffer = ["I1"]
    assert d.is_within_setpoint() is False
    assert res.buffer == ["RI"]

    # state
    res.buffer = ["I0"]
    assert d.get_state() == "TEMP_REACHED"
    assert res.buffer == ["RI"]

    res.buffer = ["I1"]
    assert d.get_state() == "HEATING"
    assert res.buffer == ["RI"]

    res.buffer = ["I2"]
    assert d.get_state() == "COOLING"
    assert res.buffer == ["RI"]

    res.buffer = ["I8"]
    assert d.get_state() == "ERROR"
    assert res.buffer == ["RI"]

    res.buffer = ["I9"]
    assert d.get_state() == "UNKNOWN"
    assert res.buffer == ["RI"]

    # dewpoint control
    res.buffer = ["D1"]
    assert d.set_dewpoint_control(True) is None
    assert res.buffer == ["SD1"]

    res.buffer = ["D0"]
    assert d.set_dewpoint_control(False) is None
    assert res.buffer == ["SD0"]

    # configure
    res.buffer = ["T+250", "D1", "O1"]
    assert (
        d.configure(
            {
                "setpoint.temperature": 25.0,
                "dewpoint_control.enabled": True,
            }
        )
        is None
    )
    assert res.buffer == ["ST+0250", "SD1", "SO1"]

    # events
    res.buffer = ["T+300"]
    assert d.handle_event(ChangeTargetTemperature(30.0)) is None
    assert res.buffer == ["ST+0300"]

    res.buffer = ["D1"]
    assert d.handle_event(ChangeDewpointControl(True)) is None
    assert res.buffer == ["SD1"]

    with pytest.raises(ValueError):
        d.handle_event(object())
