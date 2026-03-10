from diode_measurement.driver.k6514 import K6514

from . import res


def test_driver_k6514(res):
    d = K6514(res)

    res.buffer = ["Keithley Model 6514\r"]
    assert d.identify() == "Keithley Model 6514"
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
    assert d.set_sense_average_tcontrol("MOV") is None
    assert res.buffer == [":SENS:AVER:TCON MOV", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_average_count(42) is None
    assert res.buffer == [":SENS:AVER:COUN 42", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_average_state(True) is None
    assert res.buffer == [":SENS:AVER:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_nplcycles(0.42) is None
    assert res.buffer == [":SENS:CURR:NPLC 4.200000E-01", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_zero_check_enabled(True) is None
    assert res.buffer == [":SYST:ZCH 1", "*OPC?"]
