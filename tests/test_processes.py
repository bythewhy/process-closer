import psutil

from process_closer.models import ProcessRef
from process_closer.processes import ProcessCloser


class ProcessStub:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_wait_falls_back_when_windows_denies_wait(monkeypatch) -> None:
    def deny_wait(processes, timeout):
        raise psutil.AccessDenied(processes[0].pid)

    monkeypatch.setattr(psutil, "wait_procs", deny_wait)
    monkeypatch.setattr(psutil, "pid_exists", lambda pid: False)
    closer = ProcessCloser(0)
    ref = ProcessRef(42, "app.exe", 10.0)

    assert closer._wait([(ref, ProcessStub(42))]) == set()
