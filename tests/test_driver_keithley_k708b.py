from diode_measurement.drivers.keithley.k708b import K708BAdapter


def test_k708b_adapter(res):
    d = K708BAdapter(res)

    res.buffer = ["Keithley Model 708B\r"]
    assert d.identify() == "Keithley Model 708B"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]

    res.buffer = ["1"]
    assert d.open_all_channels() is None
    assert res.buffer == ['channel.open("allslots")', "*OPC?"]

    res.buffer = ["1"]
    assert d.close_channels(["1B02"]) is None
    assert res.buffer == ['channel.close("1B02")', "*OPC?"]
