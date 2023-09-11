import pytest

from diode_measurement import utils


def test_get_resource():
    assert utils.get_resource("16") == ("GPIB0::16::INSTR", "")
    assert utils.get_resource("GPIB::13::INSTR") == ("GPIB::13::INSTR", "")
    assert utils.get_resource("localhost:10001") == ("TCPIP0::localhost::10001::SOCKET", "@py")
    assert utils.get_resource("192.168.0.1:10002") == ("TCPIP0::192.168.0.1::10002::SOCKET", "@py")
    assert utils.get_resource("TCPIP::192.168.0.1::1080::SOCKET") == ("TCPIP::192.168.0.1::1080::SOCKET", "@py")


def test_safe_filename():
    assert utils.safe_filename("Monty Python's!") == "Monty_Python_s_"
    assert utils.safe_filename("$2020-02-22 13:14:25") == "_2020-02-22_13_14_25"


def test_auto_scale():
    assert utils.auto_scale(1024) == (1e3, "k", "kilo")
    assert utils.auto_scale(256) == (1e0, "", "")
    assert utils.auto_scale(0) == (1e0, "", "")
    assert utils.auto_scale(0.042) == (1e-3, "m", "milli")
    assert utils.auto_scale(0.00042) == (1e-6, "u", "micro")


def test_format_metric():
    assert utils.format_metric(0.0042, "A") == "4.200 mA"
    assert utils.format_metric(0.0042, "A", 1) == "4.2 mA"


def test_format_switch():
    assert utils.format_switch(0) == "OFF"
    assert utils.format_switch(1) == "ON"


def test_limits():
    assert utils.limits([]) == tuple()
    assert utils.limits([[4, 2]]) == (4, 4, 2, 2)
    assert utils.limits([[4, 5], [4, 3], [-1, 2]]) == (-1, 4, 2, 5)
    assert utils.limits([[-1, 2], [4, 5], [4, 3]]) == (-1, 4, 2, 5)
    assert utils.limits([[1, -2], [4, -5], [4, -3]]) == (1, 4, -5, -2)


def test_inverse_square():
    with pytest.raises(ZeroDivisionError):
        utils.inverse_square(0)
    assert utils.inverse_square(1) == 1
    assert utils.inverse_square(2) == .25
    assert utils.inverse_square(8) == .015625
