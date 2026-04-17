"""Example: start a continuous IV measurement and monitor it for 10 seconds."""

import time

from rpc_client import DiodeMeasurementClient


client = DiodeMeasurementClient("localhost", 4000)

# Wait until the system is idle
print("Waiting for 'idle' state...")
while client.current_state() != "idle":
    time.sleep(1)

# Start a measurement
print("Starting measurement...")
client.start(
    measurement_type="iv",
    measurement_instruments=["smu"],
    continuous=True,
)

# Wait for the expected state transitions
print("Waiting for 'configure' state...")
while client.current_state() != "configure":
    time.sleep(1)

print("Waiting for 'ramping' state...")
while client.current_state() != "ramping":
    time.sleep(1)

print("Waiting for 'continuous' state...")
while client.current_state() != "continuous":
    time.sleep(1)

# Monitor for 10 seconds
print("Monitoring measurement for 10 seconds...")
start_time = time.monotonic()

while time.monotonic() - start_time < 10:
    if client.current_state() != "continuous":
        print("Measurement stopped early.")
        break

    print(client.state())
    time.sleep(1)

# Stop the measurement
print("Stopping measurement...")
client.stop()

# Wait until the system is idle again
print("Waiting for 'idle' state...")
while client.current_state() != "idle":
    time.sleep(1)

print("Done!")
