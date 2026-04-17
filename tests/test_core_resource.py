from diode_measurement.core.resource import Resource


def test_resource():
    res = Resource("TCPIP::localhost:8080::SOCKET", "@sim")
    assert res.resource_name == "TCPIP::localhost:8080::SOCKET"
    assert res.visa_library == "@sim"
    assert res.options == {
        "read_termination": "\r\n",
        "write_termination": "\r\n",
        "timeout": 8000
    }


def test_resource_options():
    res = Resource("GPIB::8::INSTR", "", read_termination="\n", timeout=2000, foo=42)
    assert res.resource_name == "GPIB::8::INSTR"
    assert res.visa_library == ""
    assert res.options == {
        "read_termination": "\n",
        "write_termination": "\r\n",
        "timeout": 2000,
        "foo": 42,
    }
