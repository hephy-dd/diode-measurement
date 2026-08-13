"""Example: start a continuous CV measurement."""

import time

from rpc_client import DiodeMeasurementClient

client = DiodeMeasurementClient("localhost", 4000)

frequencies = [
    1_000,
    10_000,
    100_000,
    1_000_000,
]

print("Waiting for 'idle' state...")
while client.current_state() != client.IDLE:
    time.sleep(1)

for frequency in frequencies:
    lcr_options = {
        "voltage": 0.1,
        "frequency": frequency,
    }
    client.instrument_update("lcr", lcr_options)

    print(f"Starting CV scan at {frequency} Hz...")

    client.start(
        sample="DIODE_002",
        measurement_type="cv_diode",
        measurement_instruments=["smu", "lcr"],
        begin_voltage=0,
        end_voltage=10,
        step_voltage=0.25,
    )

    time.sleep(1)

    print("Waiting for scan to finish...")
    while client.current_state() != client.IDLE:
        time.sleep(1)

print("Done!")
