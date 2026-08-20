from comet.driver.generic import InstrumentError


class SCPIParseError(ValueError): ...


def parse_scpi_error(response: str) -> InstrumentError | None:
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
