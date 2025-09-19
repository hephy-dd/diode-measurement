from diode_measurement.driver.k4215 import K4215
import pytest

from . import res


def test_driver_k4215_basic_operations(res):
    """Test basic driver operations."""
    d = K4215(res)

    # Test identity
    res.buffer = ["KEITHLEY INSTRUMENTS,KI4200A,1489223,V1.14"]
    assert d.identity() == "KEITHLEY INSTRUMENTS,KI4200A,1489223,V1.14"
    assert res.buffer == ["*IDN?"]

    # Test reset
    res.buffer = []
    assert d.reset() is None
    assert res.buffer == ["*RST"]

    # Test clear
    res.buffer = []
    assert d.clear() is None
    assert res.buffer == ["BC"]

    # Test finalize
    res.buffer = []
    assert d.finalize() is None
    assert res.buffer == ["*RST"]


def test_driver_k4215_error_handling(res):
    """Test error handling functionality."""
    d = K4215(res)

    # Test no error
    res.buffer = [""]
    assert d.next_error() == (0, "No error")
    assert res.buffer == [":ERROR:LAST:GET", ":ERROR:LAST:CLEAR"]

    # Test error code and text parsing
    res.buffer = ["KXCI command error. (-992)"]
    assert d.next_error() == (-992, "KXCI command error")
    assert res.buffer == [":ERROR:LAST:GET", ":ERROR:LAST:CLEAR"]

    # Test unparseable error format
    res.buffer = ["Unknown error format with some text"]
    result = d.next_error()
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result == (-1, "Unknown error format with some text")
    assert res.buffer == [":ERROR:LAST:GET", ":ERROR:LAST:CLEAR"]


def test_driver_k4215_output_control(res):
    """Test output enable/disable functionality."""
    d = K4215(res)

    # Test get output enabled - True
    res.buffer = ["1"]
    # always returns False for K4215, as the command is not implemented
    # and no querying to the K4215 takes place
    assert d.get_output_enabled() is False 
    assert res.buffer == ["1"]

    # Test get output enabled - False
    # always returns False for K4215, as the command is not implemented
    # and no querying to the K4215 takes place
    res.buffer = ["0"]
    assert d.get_output_enabled() is False
    assert res.buffer == ["0"]

    # Test set output enabled - True
    res.buffer = []
    assert d.set_output_enabled(True) is None
    assert res.buffer == [":CVU:OUTPUT 1"]

    # Test set output enabled - False
    res.buffer = []
    assert d.set_output_enabled(False) is None
    assert res.buffer == [":CVU:OUTPUT 0"]


def test_driver_k4215_voltage_level(res):
    """Test voltage level and range control."""
    d = K4215(res)

    # Test get voltage level
    res.buffer = ["2.200000E+01"]
    assert d.get_voltage_level() == 22.0
    assert res.buffer == [":CVU:DCV?"]

    # Test set voltage level
    res.buffer = []
    assert d.set_voltage_level(22.0) is None
    assert res.buffer == [":CVU:DCV 2.200E+01"]

    # Test set voltage level with negative value
    res.buffer = []
    assert d.set_voltage_level(-5.5) is None
    assert res.buffer == [":CVU:DCV -5.500E+00"]

    # check exception for out-of-range voltage level
    with pytest.raises(ValueError):
        d.set_voltage_level(35.0)  # Above max 30V
    with pytest.raises(ValueError):
        d.set_voltage_level(-35.0)  # Below min -30V


def test_driver_k4215_voltage_offset(res):
    """Test voltage offset control."""
    d = K4215(res)

    # Test get voltage offset
    res.buffer = ["1.500000E+00"]
    assert d.get_voltage_offset() == 1.5
    assert res.buffer == [":CVU:DCV:OFFSET?"]

    # Test set voltage offset
    res.buffer = []
    assert d.set_voltage_offset(1.5) is None
    assert res.buffer == [":CVU:DCV:OFFSET 1.500E+00"]

    # Test set voltage offset with negative value
    res.buffer = []
    assert d.set_voltage_offset(-2.0) is None
    assert res.buffer == [":CVU:DCV:OFFSET -2.000E+00"]

    # check exception for out-of-range voltage level
    with pytest.raises(ValueError):
        d.set_voltage_level(35.0)  # Above max 30V
    with pytest.raises(ValueError):
        d.set_voltage_level(-35.0)  # Below min -30V


def test_driver_k4215_amplitude(res):
    """Test AC amplitude voltage and frequency control."""
    d = K4215(res)

    # Test set amplitude voltage
    res.buffer = []
    assert d.set_amplitude_voltage(0.2) is None
    assert res.buffer == [":CVU:ACV 2.000000E-01"]

    # Test set amplitude voltage with small value
    res.buffer = []
    assert d.set_amplitude_voltage(0.05) is None
    assert res.buffer == [":CVU:ACV 5.000000E-02"]

    # check out of range voltage values
    with pytest.raises(ValueError):
        d.set_amplitude_voltage(1.5)  # Above max 1V
    with pytest.raises(ValueError):
        d.set_amplitude_voltage(0.005)  # Below min 10mV


def test_driver_k4215_frequency(res):
    """Test AC frequency control."""
    d = K4215(res)

    res.buffer = []
    assert d.set_amplitude_frequency(1.2e3) is None
    assert res.buffer == [":CVU:FREQ 1200"]

    res.buffer = []
    assert d.set_amplitude_frequency(1e6) is None
    assert res.buffer == [":CVU:FREQ 1000000"]

    # check out of range frequency values
    with pytest.raises(ValueError):
        d.set_amplitude_frequency(5e7)  # Above max 10MHz
    with pytest.raises(ValueError):
        d.set_amplitude_frequency(5e2)  # Below min 1kHz


def test_driver_k4215_impedance_functions(res):
    """Test impedance type and measurement functions."""
    d = K4215(res)

    # Test impedance type with string (CPRP maps to 2)
    res.buffer = []
    assert d.set_function_impedance_type("CPRP") is None
    assert res.buffer == [":CVU:MODEL 2"]

    # Test impedance type with string (CPGP also maps to 2)
    res.buffer = []
    assert d.set_function_impedance_type("CPGP") is None
    assert res.buffer == [":CVU:MODEL 2"]

    # Test impedance type with string (CSRS maps to 3)
    res.buffer = []
    assert d.set_function_impedance_type("CSRS") is None
    assert res.buffer == [":CVU:MODEL 3"]

    # Test impedance type with string (ZTHETA maps to 0)
    res.buffer = []
    assert d.set_function_impedance_type("ZTHETA") is None
    assert res.buffer == [":CVU:MODEL 0"]

    # Test impedance type with string (RPLUSJX maps to 1)
    res.buffer = []
    assert d.set_function_impedance_type("RPLUSJX") is None
    assert res.buffer == [":CVU:MODEL 1"]

    # Test impedance type with string (CPD maps to 4)
    res.buffer = []
    assert d.set_function_impedance_type("CPD") is None
    assert res.buffer == [":CVU:MODEL 4"]

    # Test impedance type with string (CSD maps to 5)
    res.buffer = []
    assert d.set_function_impedance_type("CSD") is None
    assert res.buffer == [":CVU:MODEL 5"]

    # Test impedance type with string (YTHETA maps to 7)
    res.buffer = []
    assert d.set_function_impedance_type("YTHETA") is None
    assert res.buffer == [":CVU:MODEL 7"]

    # Test impedance type with integer
    res.buffer = []
    assert d.set_function_impedance_type(3) is None
    assert res.buffer == [":CVU:MODEL 3"]

    # Test impedance type with invalid string (should default to 2)
    res.buffer = []
    assert d.set_function_impedance_type("INVALID") is None
    assert res.buffer == [":CVU:MODEL 2"]


def test_driver_k4215_aperture_control(res):
    """Test aperture, filter, and delay control."""
    d = K4215(res)

    # Test default aperture settings - default is aperture=10, filter_factor=1, delay_factor=1
    res.buffer = []
    assert d.set_aperture() is None
    assert res.buffer == [":CVU:SPEED 3,1.000E+00,1.000E+00,1.000E+01"]

    # Test custom aperture settings
    res.buffer = []
    assert d.set_aperture(aperture=5, filter_factor=2, delay_factor=3) is None
    assert res.buffer == [":CVU:SPEED 3,3.000E+00,2.000E+00,5.000E+00"]

    # Test aperture with different values
    res.buffer = []
    assert d.set_aperture(aperture=8, filter_factor=4, delay_factor=2) is None
    assert res.buffer == [":CVU:SPEED 3,2.000E+00,4.000E+00,8.000E+00"]

    # check out of range aperture values
    with pytest.raises(ValueError):
        d.set_aperture(aperture=0.001)  # Below min 0.006
    with pytest.raises(ValueError):
        d.set_aperture(aperture=11)  # Above max 10.002

    # check out of range filter_factor values
    with pytest.raises(ValueError):
        d.set_aperture(filter_factor=-1)  # Below min 0
    with pytest.raises(ValueError):
        d.set_aperture(filter_factor=800)  # Above max 707

    # check out of range delay_factor values
    with pytest.raises(ValueError):
        d.set_aperture(delay_factor=-1)  # Below min 0
    with pytest.raises(ValueError):
        d.set_aperture(delay_factor=150)  # Above max 100


def test_driver_k4215_correction_functions(res):
    """Test correction and cable length functions."""
    d = K4215(res)

    # Test correction - all disabled (format: open,short,load)
    res.buffer = []
    assert d.set_correction() is None
    assert res.buffer == [":CVU:CORRECT 0,0,0"]

    # Test correction - open enabled
    res.buffer = []
    assert d.set_correction(open_state=True) is None
    assert res.buffer == [":CVU:CORRECT 1,0,0"]

    # Test correction - short enabled
    res.buffer = []
    assert d.set_correction(short_state=True) is None
    assert res.buffer == [":CVU:CORRECT 0,1,0"]

    # Test correction - load enabled
    res.buffer = []
    assert d.set_correction(load_state=True) is None
    assert res.buffer == [":CVU:CORRECT 0,0,1"]

    # Test correction - multiple enabled
    res.buffer = []
    assert d.set_correction(open_state=True, short_state=True) is None
    assert res.buffer == [":CVU:CORRECT 1,1,0"]



def test_driver_k4215_correction_length_validation(res):
    """Test cable length correction with validation."""
    d = K4215(res)

    # Test valid cable lengths
    valid_lengths = [0, 1.5, 3.0]
    for length in valid_lengths:
        res.buffer = []
        assert d.set_correction_length(length) is None
        assert res.buffer == [f":CVU:LENGTH {length:.1f}"]

    # test invalid cable length
    with pytest.raises(ValueError):
        d.set_correction_length(5)
    with pytest.raises(ValueError):
        d.set_correction_length(-1)


def test_driver_k4215_aci_range(res):
    """Test ACI range setting."""
    d = K4215(res)

    for aci_range in [0, 1e-6, 30e-6, 1e-3]:
        res.buffer = []
        assert d.set_aci_range(aci_range) is None
        assert res.buffer == [f":CVU:ACZ:RANGE {aci_range:.6E}"]

    # check invalid ACI range values
    with pytest.raises(ValueError):
        d.set_aci_range(2e-3)  # Above max 1mA
    with pytest.raises(ValueError):
        d.set_aci_range(0.5e-6)  # Below min 1uA


def test_driver_k4215_impedance_measurement(res):
    """Test impedance measurement functionality."""
    d = K4215(res)

    # Test successful impedance measurement - _fetch() directly queries :CVU:MEASZ?
    res.buffer = ["1.000000E-01,2.000000E-01"]
    result = d.measure_impedance()
    assert result == (0.1, 0.2)
    # Check that measurement command was sent
    assert res.buffer == [":CVU:MEASZ?"]

    # Test impedance measurement with different values
    res.buffer = ["5.500000E-03,-1.200000E-02"]
    result = d.measure_impedance()
    assert result == (0.0055, -0.012)
    assert res.buffer == [":CVU:MEASZ?"]


def test_driver_k4215_external_bias_tee(res):
    """Test external bias tee functionality."""
    d = K4215(res)

    # Test external bias tee configuration
    res.buffer = []  # Need enough responses for all the _write calls
    d._external_bias_tee_enabled = True
    d._enable_bias_tee_dc_voltage()
    expected_commands = [
        ":CVU:CONFIG:ACVHI 1",
        ":CVU:CONFIG:DCVHI 1",
        ":CVU:DCV:OFFSET -10",
        ":CVU:DCV -10",
    ]
    assert res.buffer == expected_commands

    # Test that setting voltage level raises error when bias tee enabled
    d._external_bias_tee_enabled = True
    with pytest.raises(RuntimeError):
        d.set_voltage_level(5.0)

    with pytest.raises(RuntimeError):
        d.set_voltage_offset(2.0)


def test_driver_k4215_abstract_methods(res):
    """Test abstract method implementations."""
    d = K4215(res)

    # Test compliance_tripped (always returns False for K4215)
    assert d.compliance_tripped() is False

    # Test measure_i (not supported, returns 0.0)
    assert d.measure_i() == 0.0

    # Test measure_iv (not supported, returns 0.0, 0.0)
    assert d.measure_iv() == (0.0, 0.0)

    # Test set_current_compliance_level (no-op for K4215)
    assert d.set_current_compliance_level(0.1) is None


def test_driver_k4215_default_configuration(res):
    """Test comprehensive configuration with all options."""
    d = K4215(res)

    res.buffer = [] 
    options = {"voltage": 0.1, "frequency": 100000.0}
    d.configure(options)

    assert ":CVU:MODE 0" in res.buffer  # CVU mode set
    assert ":CVU:MODEL 2" in res.buffer  # Default CPRP function type
    assert ":CVU:ACV 1.000000E-01" in res.buffer  # AC voltage
    assert ":CVU:FREQ 100000" in res.buffer  # Frequency



def test_driver_k4215_fetch_functionality(res):
    """Test _fetch method for measurement operations."""
    d = K4215(res)

    # _fetch directly queries :CVU:MEASZ?
    res.buffer = ["1.000000E-01,2.000000E-01"]
    result = d._fetch(timeout=1.0, interval=0.1)
    assert result == "1.000000E-01,2.000000E-01"
    assert res.buffer == [":CVU:MEASZ?"]

