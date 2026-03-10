from diode_measurement.driver.k237 import K237

from . import res


def test_driver_k237(res):
    d = K237(res)
    d.WRITE_DELAY = 0  # disable for tests

    res.buffer = ["K237A1\r"]
    assert d.identify() == "K237A1"
    assert res.buffer == ["U0X"]

    res.buffer = []
    assert d.reset() is None
    assert res.buffer == []

    res.buffer = []
    assert d.clear() is None
    assert res.buffer == []

    res.buffer = ["23700000000000000000000000000"]
    assert d.next_error() is None
    assert res.buffer == ["U1X"]

    res.buffer = ["23701000000000000000000000000"]
    error = d.next_error()
    assert (error.code, error.message) == (101, "IDDC")
    assert res.buffer == ["U1X"]

    res.buffer = ["23700000000001000000000000000"]
    error = d.next_error()
    assert (error.code, error.message) == (110, "In Standby")
    assert res.buffer == ["U1X"]

    res.buffer = []
    assert d.configure({}) is None
    assert res.buffer == ["F0,0X", "B0,0,0X", "P0X"]

    res.buffer = ["000000000000000000N1000000000"]
    assert d.get_output_enabled() is True
    assert res.buffer == ["U3X"]

    res.buffer = []
    assert d.set_output_enabled(True) is None
    assert res.buffer == ["N1X"]

    res.buffer = ["+4.200000E+01"]
    assert d.get_voltage_level() == 42.0
    assert res.buffer == ["G1,2,0X", "X"]

    res.buffer = []
    assert d.set_voltage_level(42.0) is None
    assert res.buffer == ["B4.200E+01,,X"]

    res.buffer = []
    assert d.set_voltage_range(200.0) is None
    assert res.buffer == ["B,4,X"]

    res.buffer = []
    assert d.set_current_compliance_level(0.002) is None
    assert res.buffer == ["L2.000E-03,0X"]

    res.buffer = ["OS000000000000000000000000000"]
    assert d.compliance_tripped() is True
    assert res.buffer == ["G1,0,0X", "X"]

    res.buffer = ["+4.210000E-03"]
    assert d.measure_i() == 0.00421
    assert res.buffer == ["G4,2,0X", "X"]

    res.buffer = ["+4.210000E-03", "+4.200000E+01"]
    assert d.measure_iv() == (0.00421, 42.0)
    assert res.buffer == ["G4,2,0X", "X", "G1,2,0X", "X"]

    assert d._voltage_range(0.1) == 1
    assert d._voltage_range(2.0) == 2
    assert d._voltage_range(100.0) == 3
    assert d._voltage_range(200.0) == 4
    assert d._voltage_range(2100.0) == 0  # auto
