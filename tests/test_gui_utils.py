from diode_measurement.gui import utils


def test_format_metric():
    assert utils.format_metric(0.0042, "A") == "4.200 mA"
    assert utils.format_metric(0.0042, "A", 1) == "4.2 mA"


def test_format_switch():
    assert utils.format_switch(False) == "OFF"
    assert utils.format_switch(True) == "ON"
