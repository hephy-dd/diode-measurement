import pytest

from diode_measurement.driver.a4284a import A4284A

from . import res


def test_driver_a4284a(res):
    d = A4284A(res)

    res.buffer = ["Agilent Model A4284A\r"]
    assert d.identity() == "Agilent Model A4284A"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]

    res.buffer = ["0,\"No error\""]
    assert d.next_error() == (0, "No error")
    assert res.buffer == [":SYST:ERR?"]

    res.buffer = ["1"]
    assert d.get_output_enabled() is True
    assert res.buffer == [":BIAS:STAT?"]

    res.buffer = ["1"]
    assert d.set_output_enabled(True) is None
    assert res.buffer == [":BIAS:STAT 1", "*OPC?"]

    res.buffer = ["4.200000E+01"]
    assert d.get_voltage_level() == 42.0
    assert res.buffer == [":BIAS:VOLT:LEV?"]

    res.buffer = ["1"]
    assert d.set_voltage_level(42.0) is None
    assert res.buffer == [":BIAS:VOLT:LEV 4.200E+01", "*OPC?"]

    res.buffer = []  # TODO
    assert d.set_voltage_range(200.0) is None
    assert res.buffer == []

    res.buffer = []  # not supported
    assert d.set_current_compliance_level(0.002) is None
    assert res.buffer == []

    res.buffer = []
    assert not d.compliance_tripped()
    assert res.buffer == []

    res.buffer = []
    assert d.measure_i() == 0.0
    assert res.buffer == []

    res.buffer = []
    assert d.measure_iv() == (0.0, 0.0)
    assert res.buffer == []

    res.buffer = ["1", "0", "1", "1.000000E-01,2.000000E-01"]
    assert d.measure_impedance() == (0.1, 0.2)
    assert res.buffer == ["*CLS", "*OPC?", "*OPC", ":TRIG:IMM", "*ESR?", "*ESR?", ":FETC?"]

    res.buffer = ["1"]
    assert d.set_function_impedance_type("CPRP") is None
    assert res.buffer == [":FUNC:IMP:TYPE CPRP", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_aperture("MED", 42) is None
    assert res.buffer == [":APER MED,42", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_correction_length(2) is None
    assert res.buffer == [":CORR:LENG 2", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_correction_open_state(True) is None
    assert res.buffer == [":CORR:OPEN:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_correction_short_state(True) is None
    assert res.buffer == [":CORR:SHOR:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_amplitude_voltage(4.2) is None
    assert res.buffer == [":VOLT 4.200000E+00", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_amplitude_frequency(1.2e3) is None
    assert res.buffer == [":FREQ 1.200000E+03", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_amplitude_alc(True) is None
    assert res.buffer == [":AMPL:ALC 1", "*OPC?"]
