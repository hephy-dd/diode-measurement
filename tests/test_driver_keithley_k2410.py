from diode_measurement.drivers.keithley.k2410 import K2410Adapter


def test_k2410_adapter(res):
    d = K2410Adapter(res)

    res.buffer = ["Keithley Model 2410\r"]
    assert d.identify() == "Keithley Model 2410"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]
