from diode_measurement.drivers.hephy.brandbox import BrandBoxAdapter


def test_brandbox_adapter(res):
    d = BrandBoxAdapter(res)

    res.buffer = ["HEPHY BrandBox v1\r"]
    assert d.identify() == "HEPHY BrandBox v1"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["OK"]
    assert d.reset() is None
    assert res.buffer == ["*RST"]

    res.buffer = ["OK"]
    assert d.clear() is None
    assert res.buffer == ["*CLS"]
