from diode_measurement.core.resource import parse_resource, Resource


def test_parse_resource():
    assert parse_resource("16") == ("GPIB0::16::INSTR", "")
    assert parse_resource("GPIB::13::INSTR") == ("GPIB::13::INSTR", "")
    assert parse_resource("localhost:10001") == ("TCPIP0::localhost::10001::SOCKET", "@py")
    assert parse_resource("192.168.0.1:10002") == ("TCPIP0::192.168.0.1::10002::SOCKET", "@py")
    assert parse_resource("TCPIP::192.168.0.1::1080::SOCKET") == ("TCPIP::192.168.0.1::1080::SOCKET", "@py")


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
