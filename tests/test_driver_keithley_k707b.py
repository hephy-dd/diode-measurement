from diode_measurement.drivers.keithley.k707b import K707BAdapter


def test_k707b_adapter(res):
    d = K707BAdapter(res)

    res.buffer = ["Keithley Model 707B\r"]
    assert d.identify() == "Keithley Model 707B"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]
