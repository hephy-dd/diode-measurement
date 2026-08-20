from comet.driver.generic import InstrumentError

__all__ = ["SCPIParseError", "parse_scpi_error"]


class SCPIParseError(ValueError):
    """Raised when an SCPI error response cannot be parsed."""


def parse_scpi_error(response: str) -> InstrumentError | None:
    """Parse an SCPI error response.

    The expected format is ``<code>,<message>``. A zero error code indicates
    that no error occurred.

    Args:
        response: Raw SCPI error response.

    Returns:
        An instrument error, or ``None`` if the error code is zero.

    Raises:
        SCPIParseError: If the response is malformed.
    """
    try:
        code_text, message_text = response.strip().split(",", 1)
        code = int(code_text.strip())
    except (ValueError, TypeError) as exc:
        raise SCPIParseError(f"Malformed SYST:ERR? response: {response!r}") from exc

    if code == 0:
        return None

    message_text = message_text.strip()
    if message_text.startswith('"') and message_text.endswith('"'):
        message_text = message_text[1:-1]

    return InstrumentError(code, message_text)
