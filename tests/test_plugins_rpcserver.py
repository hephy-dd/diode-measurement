from diode_measurement.plugins.rpcserver import is_finite, json_dict


def test_is_finite():
    assert is_finite(0)
    assert is_finite(-42.)
    assert is_finite("foo")
    assert not is_finite(float("nan"))
    assert not is_finite(float("+inf"))
    assert not is_finite(float("-inf"))


def test_json_dict():
    data_in = {"a": float("nan"), "b": 42., "c": "42"}
    data_out = {"a": None, "b": 42., "c": "42"}
    assert json_dict(data_in) == data_out
