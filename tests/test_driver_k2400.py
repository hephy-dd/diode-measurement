from diode_measurement.driver.k2400 import K2400

from . import FakeResource


class TestDriverK2400:

    def test_driver_k2400(self):
        res = FakeResource()
        d = K2400(res)

        res.buffer = ["Keithley Model 2400\r"]
        assert d.identity() == "Keithley Model 2400"
        assert res.buffer == ["*IDN?"]

        res.buffer = ["1"]
        assert d.reset() is None
        assert res.buffer == ["*RST", "*OPC?"]

        res.buffer = ["1"]
        assert d.clear() is None
        assert res.buffer == ["*CLS", "*OPC?"]
