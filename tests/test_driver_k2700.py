from diode_measurement.driver.k2700 import K2700

from . import res


def test_driver_k2700(res):
    d = K2700(res)

    res.buffer = ["Keithley Model 2700\r"]
    assert d.identify() == "Keithley Model 2700"
    assert res.buffer == ["*IDN?"]

    res.buffer = []  # Reset disabled!
    assert d.reset() is None
    assert res.buffer == []

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]
