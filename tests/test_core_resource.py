from diode_measurement.core.resource import Resource, ResourceConfig, parse_resource


def test_parse_resource():
    assert parse_resource("16") == ("GPIB0::16::INSTR", "")
    assert parse_resource("GPIB::13::INSTR") == ("GPIB::13::INSTR", "")
    assert parse_resource("localhost:10001") == (
        "TCPIP0::localhost::10001::SOCKET",
        "@py",
    )
    assert parse_resource("192.168.0.1:10002") == (
        "TCPIP0::192.168.0.1::10002::SOCKET",
        "@py",
    )
    assert parse_resource("TCPIP::192.168.0.1::1080::SOCKET") == (
        "TCPIP::192.168.0.1::1080::SOCKET",
        "@py",
    )


def test_resource_config():
    cfg = ResourceConfig("ASRL5::INSTR", "@py", termination="\n", timeout=2.0)
    assert cfg.resource_name == "ASRL5::INSTR"
    assert cfg.visa_library == "@py"
    assert cfg.termination == "\n"
    assert cfg.timeout == 2.0


def test_resource():
    cfg = ResourceConfig("TCPIP::localhost:8080::SOCKET", "@sim")
    res = Resource(cfg)
    assert res._resource_config == cfg
    assert res.resource_name == "TCPIP::localhost:8080::SOCKET"
