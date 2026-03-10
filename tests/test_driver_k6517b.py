from diode_measurement.driver.k6517b import K6517B

from . import res


def test_driver_k6517b(res):
    d = K6517B(res)

    res.buffer = ["Keithley Model 6517B\r"]
    assert d.identify() == "Keithley Model 6517B"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]

    res.buffer = ["0,\"no error\""]
    assert d.next_error() is None
    assert res.buffer == [":SYST:ERR?"]

    res.buffer = ["1"]
    assert d.set_format_elements(["VOLT", "CURR"]) is None
    assert res.buffer == [":FORM:ELEM VOLT,CURR", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_function("VOLT") is None
    assert res.buffer == [":SENS:FUNC 'VOLT'", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_range(4.2e-3) is None
    assert res.buffer == [":SENS:CURR:RANG 4.200000E-03", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_range_auto(True) is None
    assert res.buffer == [":SENS:CURR:RANG:AUTO 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_average_tcontrol("MOV") is None
    assert res.buffer == [":SENS:CURR:AVER:TCON MOV", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_average_count(42) is None
    assert res.buffer == [":SENS:CURR:AVER:COUN 42", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_average_state(True) is None
    assert res.buffer == [":SENS:CURR:AVER:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_nplcycles(0.42) is None
    assert res.buffer == [":SENS:CURR:NPLC 4.200000E-01", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_zero_check_enabled(True) is None
    assert res.buffer == [":SYST:ZCH 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_output_enabled(True) is None
    assert res.buffer == [":OUTP:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.get_output_enabled() is True
    assert res.buffer == [":OUTP:STAT?"]

    res.buffer = ["1"]
    assert d.set_voltage_level(4.2e-3) is None
    assert res.buffer == [":SOUR:VOLT:LEV 4.200000E-03", "*OPC?"]

    res.buffer = ["4.200000E-03"]
    assert d.get_voltage_level() == 4.2e-3
    assert res.buffer == [":SOUR:VOLT:LEV?"]

    res.buffer = ["1"]
    assert d.set_voltage_range(4.2e-3) is None
    assert res.buffer == [":SOUR:VOLT:RANG 4.200000E-03", "*OPC?"]

    res.buffer = ["0"]
    assert d.compliance_tripped() is False
    assert res.buffer == [":SOUR:CURR:LIM?"]
