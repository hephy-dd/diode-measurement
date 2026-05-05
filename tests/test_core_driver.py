from diode_measurement.core.driver import BaseDriver
from diode_measurement.core.resource import Resource, ResourceConfig


def test_base_driver():
    config = ResourceConfig("ASRL4::INSTR")
    resource = Resource(config)
    driver = BaseDriver(resource)
    assert driver.resource is resource
