import logging
from concurrent.futures import Future
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any

__all__ = ["ThreadingActor", "ActorNotRunningError"]

logger = logging.getLogger(__name__)


class ActorNotRunningError(RuntimeError): ...


@dataclass(frozen=True, slots=True)
class Envelope:
    message: Any
    future: Future[Any]


class ThreadingActor:
    def __init__(self, abort_event: Event | None = None) -> None:
        self._abort_event = Event() if abort_event is None else abort_event
        self._inbox: Queue[Envelope] = Queue()
        self._thread = Thread(
            target=self._event_loop,
            name=f"{type(self).__name__}-thread",
        )

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self, timeout: float | None = None) -> None:
        self._abort_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout)

    def ask(self, message: Any) -> Future[Any]:
        future: Future[Any] = Future()

        if self._abort_event.is_set() or not self._thread.is_alive():
            future.set_exception(ActorNotRunningError())
            return future

        self._inbox.put_nowait(Envelope(message, future))
        return future

    def sleep(self, seconds: float) -> None:
        self._abort_event.wait(seconds)

    def on_idle(self) -> None: ...

    def on_message(self, message: Any) -> Any: ...

    def _event_loop(self) -> None:
        while not self._abort_event.is_set():
            try:
                envelope = self._inbox.get(timeout=0.1)
            except Empty:
                try:
                    self.on_idle()
                except Exception:
                    logger.exception("Failed to execute on_idle")
            except Exception:
                logger.exception("Failed to fetch inbox message")
            else:
                try:
                    result = self.on_message(envelope.message)
                except Exception as exc:
                    if not envelope.future.cancelled():
                        envelope.future.set_exception(exc)
                else:
                    if not envelope.future.cancelled():
                        envelope.future.set_result(result)
