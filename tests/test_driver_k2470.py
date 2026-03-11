from diode_measurement.driver.k2470 import K2470

from . import res


def test_driver_k2470(res):
    d = K2470(res)

    res.buffer = ["Keithley Model 2470\r"]
    assert d.identify() == "Keithley Model 2470"
    assert res.buffer == ["*IDN?"]

    res.buffer = ["1"]
    assert d.reset() is None
    assert res.buffer == ["*RST", "*OPC?"]

    res.buffer = ["1"]
    assert d.clear() is None
    assert res.buffer == ["*CLS", "*OPC?"]

    res.buffer = ["0,\"no error;;\""]
    assert d.next_error() is None
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
    assert res.buffer == [":SOUR:VOLT:ILIM:LEV 2.000E-03", "*OPC?"]

    res.buffer = ["1"]
    assert d.compliance_tripped() is True
    assert res.buffer == [":SOUR:VOLT:ILIM:LEV:TRIP?"]

    res.buffer = ["1", "+4.210000E+01,+4.210000E-03"]
    assert d.measure_i() == 0.00421
    assert res.buffer == [
        ":TRAC:TRIG \"defbuffer1\"",
        "*OPC?",
        ":TRAC:DATA? 1, 1, \"defbuffer1\", SOUR, READ",
    ]

    res.buffer = ["1", "+4.210000E+01,+4.210000E-03"]
    assert d.measure_v() == 42.1
    assert res.buffer == [
        ":TRAC:TRIG \"defbuffer1\"",
        "*OPC?",
        ":TRAC:DATA? 1, 1, \"defbuffer1\", SOUR, READ",
    ]

    res.buffer = ["1", "+4.210000E+01,+4.210000E-03"]
    assert d.measure_iv() == (0.00421, 42.1)
    assert res.buffer == [
        ":TRAC:TRIG \"defbuffer1\"",
        "*OPC?",
        ":TRAC:DATA? 1, 1, \"defbuffer1\", SOUR, READ",
    ]

    res.buffer = ["1"]
    assert d.set_route_terminals("REAR") is None
    assert res.buffer == [":ROUT:TERM REAR", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_source_function("VOLT") is None
    assert res.buffer == [":SOUR:FUNC VOLT", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_function("CURR") is None
    assert res.buffer == [":SENS:FUNC \"CURR\"", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_average_tcontrol("MOV") is None
    assert res.buffer == [":SENS:CURR:AVER:TCON MOV", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_average_count(42) is None
    assert res.buffer == [":SENS:CURR:AVER:COUN 42", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_average_enable(True) is None
    assert res.buffer == [":SENS:CURR:AVER:STAT 1", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_sense_current_nplc(4.2) is None
    assert res.buffer == [":SENS:CURR:NPLC 4.200000E+00", "*OPC?"]

    res.buffer = ["1"]
    assert d.set_system_breakdown_protection(True) is None
    assert res.buffer == [":SYST:BRE:PROT ON", "*OPC?"]

    res.buffer = ["1"]
    assert d.is_interlock() is True
    assert res.buffer == [":OUTP:INT:TRIP?"]
