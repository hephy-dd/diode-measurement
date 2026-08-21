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

    res.buffer = ["1"]
    assert d.open_all_channels() is None
    assert res.buffer == ['channel.open("allslots")', "*OPC?"]

    res.buffer = ["1"]
    assert d.close_channels(["2B01", "4B02"]) is None
    assert res.buffer == ['channel.close("2B01,4B02")', "*OPC?"]
