from diode_measurement.drivers.cts.itc import ITCAdapter


def test_itc_adapter(raw_res):
    d = ITCAdapter(raw_res)

    raw_res.out_buffer = b"T01012001000000"
    assert d.identify() == "ITC climate chamber"
    assert raw_res.in_buffer == b"T"
