import math

from diode_measurement.driver.k595 import K595

from . import res


def test_driver_k595(res):
    d = K595(res)
    d.WRITE_DELAY = 0  # disable for tests

    res.buffer = ["595\r"]
    assert d.identify() == "595"
    assert res.buffer == ["U0X"]

    res.buffer = []
    assert d.reset() is None
    assert res.buffer == []

    res.buffer = []
    assert d.clear() is None
    assert res.buffer == []

    res.buffer = ["59500000000000000000000000000"]
    assert d.next_error() is None
    assert res.buffer == ["U1X"]

    res.buffer = ["59510000000000000000000000000"]
    error = d.next_error()
    assert (error.code, error.message) == (100, "IDDC")
    assert res.buffer == ["U1X"]

    res.buffer = ["59501000000000000000000000000"]
    error = d.next_error()
    assert (error.code, error.message) == (101, "IDDCO")
    assert res.buffer == ["U1X"]

    res.buffer = []
    assert d.configure({}) is None
    assert res.buffer == ["T0X", "V0X"]

    res.buffer = ["0,1.000E+00"]
    assert d.get_output_enabled() is True
    assert res.buffer == ["F1X", "G1X", "X"]

    res.buffer = []
    assert d.set_output_enabled(True) is None
    assert res.buffer == []

    res.buffer = ["0,1.000E+00"]
    assert d.get_voltage_level() == 1.0
    assert res.buffer == ["F1X", "G1X", "X"]

    res.buffer = []
    assert d.set_voltage_level(1.0) is None
    assert res.buffer == ["V1.00X"]

    res.buffer = []  # TODO
    assert d.set_voltage_range(2.0) is None
    assert res.buffer == []

    res.buffer = []  # not available
    assert d.set_current_compliance_level(0.002) is None
    assert res.buffer == []

    res.buffer = ["O0000000000000000000000000000"]
    assert d.compliance_tripped() is True
    assert res.buffer == ["F1X", "G1X", "X"]

    res.buffer = ["+4.210E-03"]
    assert d.measure_i() == 0.00421
    assert res.buffer == ["F1X", "G1X", "X"]

    res.buffer = ["+4.210E-03"]
    i, v = d.measure_iv()
    assert i == 0.00421
    assert math.isnan(v)
    assert res.buffer == ["F1X", "G1X", "X"]

    res.buffer = ["1.000E-01"]
    prim, sec = d.measure_impedance()
    assert prim == 0.1
    assert math.isnan(sec)
    assert res.buffer == ["F0X", "G1X", "X"]
