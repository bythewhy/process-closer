from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Target:
    name: str | None = None
    path: str | None = None
    sha256: str | None = None
    publisher: str | None = None

    @property
    def key(self) -> str | None:
        return self.name.casefold() if self.name else None


@dataclass(frozen=True, slots=True)
class ProcessRef:
    pid: int
    name: str
    started_at: float

    @property
    def identity(self) -> tuple[int, float]:
        return self.pid, self.started_at


@dataclass(frozen=True, slots=True)
class CloseResult:
    process: ProcessRef
    closed: bool
    forced: bool = False
    reason: str | None = None
