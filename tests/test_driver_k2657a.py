from diode_measurement.driver.k2657a import K2657A

from . import res


def test_driver_k2657a(res):
    d = K2657A(res)

    res.buffer = ["Keithley Model 2657A\r"]
    assert d.identify() == "Keithley Model 2657A"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["reset()", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["status.reset()", "*OPC?"]

    res.buffer = ["0\tno error\t123\t0"]
    assert d.next_error() is None
    assert res.buffer == ["print(errorqueue.next())"]

    res.buffer = ["1"]
    assert d.get_output_enabled() is True
    assert res.buffer == ["print(smua.source.output)"]

    res.buffer = ["1"]
    assert d.set_output_enabled(True) is None
    assert res.buffer == ["smua.source.output = smua.OUTPUT_ON", "*OPC?"]

    res.buffer = ["4.200000E+01"]
    assert d.get_voltage_level() == 42.0
    assert res.buffer == ["print(smua.source.levelv)"]

    res.buffer = ["1"]
    assert d.set_voltage_level(42.0) is None
    assert res.buffer == ["smua.source.levelv = 4.200E+01", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_voltage_range(200.0) is None
    assert res.buffer == ["smua.source.rangev = 2.000E+02", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_current_compliance_level(0.002) is None
    assert res.buffer == ["smua.source.limiti = 2.000E-03", "*OPC?"]

    res.buffer = ["true"]
    assert d.compliance_tripped() is True
    assert res.buffer == ["print(smua.source.compliance)"]

    res.buffer = ["+4.210000E-03"]
    assert d.measure_i() == 0.00421
    assert res.buffer == ["print(smua.measure.i())"]

    res.buffer = ["+4.210000E+01"]
    assert d.measure_v() == 42.1
    assert res.buffer == ["print(smua.measure.v())"]

    res.buffer = ["+4.210000E-03", "+4.210000E+01"]
    assert d.measure_iv() == (0.00421, 42.1)
    assert res.buffer == ["print(smua.measure.i())", "print(smua.measure.v())"]

    res.buffer = ["1"]
    assert d.set_beeper_enable(True) is None
    assert res.buffer == ["beeper.enable = beeper.ON", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_source_function("DCVOLTS") is None
    assert res.buffer == ["smua.source.func = smua.OUTPUT_DCVOLTS", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_measure_filter_type("REPEAT_AVG") is None
    assert res.buffer == ["smua.measure.filter.type = smua.FILTER_REPEAT_AVG", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_measure_filter_count(42) is None
    assert res.buffer == ["smua.measure.filter.count = 42", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_measure_filter_enable(True) is None
    assert res.buffer == ["smua.measure.filter.enable = 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_measure_nplc(4.2) is None
    assert res.buffer == ["smua.measure.nplc = 4.200000E+00", "*OPC?"]
