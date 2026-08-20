from diode_measurement.drivers.keithley.k2700 import K2700Adapter


def test_k2700_adapter(res):
    d = K2700Adapter(res)

    res.buffer = ["Keithley Model 2700\r"]
    assert d.identify() == "Keithley Model 2700"
    assert res.buffer == ["*IDN?"]

    res.buffer = []  # Reset disabled!
    assert d.reset() is None
    assert res.buffer == []

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]
