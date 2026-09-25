from process_closer.models import CloseResult, ProcessRef, Target
from process_closer.monitor import ProcessMonitor


class ScannerStub:
    def __init__(self, refs: list[ProcessRef]) -> None:
        self.refs = refs
        self.calls = 0

    def find(self, target: Target) -> list[ProcessRef]:
        self.calls += 1
        return self.refs


class CloserStub:
    def __init__(self, results: list[CloseResult]) -> None:
        self.results = results
        self.received: list[ProcessRef] = []

    def close(self, refs: list[ProcessRef]) -> list[CloseResult]:
        self.received = refs
        return self.results


def test_once_scans_closes_and_reports() -> None:
    ref = ProcessRef(42, "app.exe", 10.0)
    result = CloseResult(ref, True)
    scanner = ScannerStub([ref])
    closer = CloserStub([result])
    reported: list[CloseResult] = []
    monitor = ProcessMonitor(scanner, closer, 0.1, reported.append)

    monitor.run(Target("app.exe"), once=True)

    assert scanner.calls == 1
    assert closer.received == [ref]
    assert reported == [result]
