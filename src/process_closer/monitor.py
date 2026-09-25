from collections.abc import Callable
from threading import Event

from process_closer.models import CloseResult, Target
from process_closer.processes import ProcessCloser, ProcessScanner


class ProcessMonitor:
    def __init__(
        self,
        scanner: ProcessScanner,
        closer: ProcessCloser,
        interval: float,
        on_result: Callable[[CloseResult], None],
    ) -> None:
        self._scanner = scanner
        self._closer = closer
        self._interval = interval
        self._on_result = on_result
        self._stopped = Event()

    def run(self, target: Target, once: bool = False) -> None:
        while not self._stopped.is_set():
            refs = self._scanner.find(target)
            for result in self._closer.close(refs):
                self._on_result(result)
            if once or self._stopped.wait(self._interval):
                return

    def stop(self) -> None:
        self._stopped.set()
