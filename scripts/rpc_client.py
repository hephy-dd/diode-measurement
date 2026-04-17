import json
import socket
from typing import Any

__version__ = "1.0.0"


class DiodeMeasurementError(Exception):
    """Raised when the diode measurement server returns an error or invalid data."""


class DiodeMeasurementClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def _recv_all(self, sock: socket.socket) -> bytes:
        """Read until the server closes the connection."""
        chunks: list[bytes] = []

        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)

        return b"".join(chunks)

    def query(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: int | str | None = None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }
        if params is not None:
            request["params"] = params

        payload = json.dumps(request).encode("utf-8")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            sock.sendall(payload)

            raw_response = self._recv_all(sock)

        if not raw_response:
            raise DiodeMeasurementError("Empty response from server")

        try:
            response = json.loads(raw_response.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise DiodeMeasurementError("Invalid JSON received from server") from exc

        if not isinstance(response, dict):
            raise DiodeMeasurementError("Response is not a JSON object")

        if "error" in response and response["error"] is not None:
            raise DiodeMeasurementError(f"JSON-RPC error: {response['error']}")

        return response

    def state(self) -> dict[str, Any]:
        response = self.query("state")
        result = response.get("result", {})
        if not isinstance(result, dict):
            raise DiodeMeasurementError("Invalid 'state' response format")
        return result

    def current_state(self) -> str | None:
        return self.state().get("state")

    def start(
        self,
        continuous: bool | None = None,
        auto_reconnect: bool | None = None,
        measurement_type: str | None = None,
        measurement_instruments: list[str] | None = None,
        begin_voltage: float | None = None,
        end_voltage: float | None = None,
        step_voltage: float | None = None,
        waiting_time: float | None = None,
        compliance: float | None = None,
        waiting_time_continuous: float | None = None,
    ) -> None:
        params: dict[str, Any] = {}

        if continuous is not None:
            params["continuous"] = continuous
        if auto_reconnect is not None:
            params["auto_reconnect"] = auto_reconnect
        if measurement_type is not None:
            params["measurement_type"] = measurement_type
        if measurement_instruments is not None:
            params["measurement_instruments"] = measurement_instruments
        if begin_voltage is not None:
            params["begin_voltage"] = begin_voltage
        if end_voltage is not None:
            params["end_voltage"] = end_voltage
        if step_voltage is not None:
            params["step_voltage"] = step_voltage
        if waiting_time is not None:
            params["waiting_time"] = waiting_time
        if compliance is not None:
            params["compliance"] = compliance
        if waiting_time_continuous is not None:
            params["waiting_time_continuous"] = waiting_time_continuous

        self.query("start", params or None)

    def stop(self) -> None:
        self.query("stop")

    def change_voltage(
        self,
        end_voltage: float,
        step_voltage: float | None = None,
        waiting_time: float | None = None,
    ) -> None:
        params: dict[str, Any] = {"end_voltage": end_voltage}

        if step_voltage is not None:
            params["step_voltage"] = step_voltage
        if waiting_time is not None:
            params["waiting_time"] = waiting_time

        self.query("change_voltage", params)
