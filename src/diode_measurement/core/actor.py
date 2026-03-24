import logging
import queue
import threading
from concurrent.futures import Future
from typing import Any, Optional

__all__ = ["Actor"]


class Actor:
    def __init__(self, abort_event: Optional[threading.Event] = None) -> None:
        self._abort_event = threading.Event() if abort_event is None else abort_event
        self._inbox: queue.Queue[tuple[Any, Future]] = queue.Queue()
        self._thread = threading.Thread(target=self._event_loop)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._abort_event.set()
        if self._thread.is_alive():
            self._thread.join()

    def ask(self, message: Any) -> Future:
        fut: Future = Future()
        self._inbox.put_nowait((message, fut))
        return fut

    def sleep(self, seconds: float) -> None:
        self._abort_event.wait(seconds)

    def on_idle(self) -> None:
        ...

    def on_message(self, message: Any) -> Any:
        ...

    def _event_loop(self) -> None:
        while not self._abort_event.is_set():
            try:
                message, fut = self._inbox.get(timeout=0.1)
            except queue.Empty:
                try:
                    self.on_idle()
                except Exception as exc:
                    logging.exception(exc)
            except Exception as exc:
                logging.exception(exc)
            else:
                try:
                    result = self.on_message(message)
                except Exception as exc:
                    fut.set_exception(exc)
                else:
                    fut.set_result(result)
