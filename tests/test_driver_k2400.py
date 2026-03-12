import pytest

from diode_measurement.drivers.k2400 import K2400

from . import res


def test_driver_k2400(res):
    d = K2400(res)

    res.buffer = ["Keithley Model 2400\r"]
    assert d.identify() == "Keithley Model 2400"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]

    res.buffer = ["0,\"No error\""]
    assert d.next_error() is None
    assert res.buffer == [":SYST:ERR?"]

    res.buffer = ["1"]  # errornous response
    with pytest.raises(RuntimeError) as excinfo:
        d.next_error()
    assert excinfo.value.args == ("Failed to parse error message: '1'", )
    assert res.buffer == [":SYST:ERR?"]

    res.buffer = ["1"]
    assert d.get_output_enabled() is True
    assert res.buffer == [":OUTP:STAT?"]

    res.buffer = ["1"]
    assert d.set_output_enabled(True) is None
    assert res.buffer == [":OUTP:STAT 1", "*OPC?"]

    res.buffer = ["4.200000E+01"]
    assert d.get_voltage_level() == 42.0
    assert res.buffer == [":SOUR:VOLT:LEV?"]

    res.buffer = ["1"]
    assert d.set_voltage_level(42.0) is None
    assert res.buffer == [":SOUR:VOLT:LEV 4.200E+01", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_voltage_range(200.0) is None
    assert res.buffer == [":SOUR:VOLT:RANG 2.000E+02", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_current_compliance_level(0.002) is None
    assert res.buffer == [":SENS:CURR:PROT:LEV 2.000E-03", "*OPC?"]

    res.buffer = ["1"]
    assert d.compliance_tripped() is True
    assert res.buffer == [":SENS:CURR:PROT:TRIP?"]

    res.buffer = ["1", "+4.210000E+01,+4.210000E-03"]  # VOLT,CURR
    assert d.measure_i() == 0.00421
    assert res.buffer == [":FORM:ELEM VOLT,CURR", "*OPC?", ":READ?"]

    res.buffer = ["+4.210000E+01,+4.210000E-03"]  # VOLT,CURR
    assert d.measure_v() == 42.1
    assert res.buffer == [":READ?"]

    res.buffer = ["+4.210000E+01,+4.210000E-03"]  # VOLT,CURR
    assert d.measure_iv() == (0.00421, 42.1)
    assert res.buffer == [":READ?"]

    res.buffer = ["1"]
    assert d.set_system_beeper_state(True) is None
    assert res.buffer == [":SYST:BEEP:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_route_terminals("REAR") is None
    assert res.buffer == [":ROUT:TERM REAR", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_source_function("VOLT") is None
    assert res.buffer == [":SOUR:FUNC VOLT", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_average_tcontrol("REP") is None
    assert res.buffer == [":SENS:AVER:TCON REP", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_average_count(42) is None
    assert res.buffer == [":SENS:AVER:COUN 42", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_average_state(True) is None
    assert res.buffer == [":SENS:AVER:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_nplc(4.2) is None
    assert res.buffer == [":SENS:CURR:NPLC 4.200000E+00", "*OPC?"]
