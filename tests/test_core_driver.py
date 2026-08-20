from diode_measurement.core.resource import Resource, ResourceConfig


def test_base_driver():
    config = ResourceConfig("ASRL4::INSTR")
    resource = Resource(config)
    assert resource.resource_name == "ASRL4::INSTR"
