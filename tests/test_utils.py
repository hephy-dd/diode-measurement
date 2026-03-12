from types import MappingProxyType

import pytest

from diode_measurement import utils


def test_get_resource():
    assert utils.get_resource("16") == ("GPIB0::16::INSTR", "")
    assert utils.get_resource("GPIB::13::INSTR") == ("GPIB::13::INSTR", "")
    assert utils.get_resource("localhost:10001") == ("TCPIP0::localhost::10001::SOCKET", "@py")
    assert utils.get_resource("192.168.0.1:10002") == ("TCPIP0::192.168.0.1::10002::SOCKET", "@py")
    assert utils.get_resource("TCPIP::192.168.0.1::1080::SOCKET") == ("TCPIP::192.168.0.1::1080::SOCKET", "@py")


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


@pytest.mark.parametrize(
    "value,expected",
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("on", True),
        ("1", True),
        ("false", False),
        ("no", False),
        ("off", False),
        ("0", False),
    ],
)
def test_get_bool_valid(value, expected):
    assert utils.get_bool(value) is expected


@pytest.mark.parametrize(
    "value",
    ["maybe", "abc", object(), [], {}],
)
def test_get_bool_invalid_returns_default(value):
    assert utils.get_bool(value, default=True) is True


def test_get_bool_none():
    assert utils.get_bool(None, default=True) is True
    assert utils.get_bool(None, default=False) is False


@pytest.mark.parametrize(
    "value,expected",
    [
        (1, 1),
        ("10", 10),
        (3.0, 3),
        (True, 1),
        (False, 0),
    ],
)
def test_get_int_valid(value, expected):
    assert utils.get_int(value) == expected


@pytest.mark.parametrize(
    "value",
    ["abc", object(), [], {}],
)
def test_get_int_invalid_returns_default(value):
    assert utils.get_int(value, default=5) == 5


def test_get_int_none():
    assert utils.get_int(None, default=7) == 7


@pytest.mark.parametrize(
    "value,expected",
    [
        (1, 1.0),
        (1.5, 1.5),
        ("3.14", 3.14),
        ("10", 10.0),
        (True, 1.0),
        (False, 0.0),
    ],
)
def test_get_float_valid(value, expected):
    assert utils.get_float(value) == expected


@pytest.mark.parametrize(
    "value",
    ["abc", object(), [], {}],
)
def test_get_float_invalid_returns_default(value):
    assert utils.get_float(value, default=2.5) == 2.5


def test_get_float_none():
    assert utils.get_float(None, default=7.5) == 7.5


@pytest.mark.parametrize(
    "value,expected",
    [
        ("abc", "abc"),
        (123, "123"),
        (True, "True"),
        (3.14, "3.14"),
    ],
)
def test_get_str_valid(value, expected):
    assert utils.get_str(value) == expected


def test_get_str_none():
    assert utils.get_str(None, default="x") == "x"


def test_get_dict_returns_dict():
    d = {"a": 1}
    assert utils.get_dict(d) is d


def test_get_dict_mapping_conversion():
    mp = MappingProxyType({"a": 1})
    result = utils.get_dict(mp)

    assert isinstance(result, dict)
    assert result == {"a": 1}


def test_get_dict_invalid_returns_default():
    default = {"x": 1}
    assert utils.get_dict("abc", default) is default


def test_get_dict_none_default():
    assert utils.get_dict(None) == {}
