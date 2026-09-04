from diode_measurement.core.utils import convert


def test_convert():
    assert convert(0.25, "mV", "V") == 0.00025
