from diode_measurement.drivers.k2410 import K2410

from . import res


def test_driver_k2410(res):
    d = K2410(res)

    res.buffer = ["Keithley Model 2410\r"]
    assert d.identify() == "Keithley Model 2410"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]
