import hashlib
import os
import subprocess
import time
from collections.abc import Iterable

import psutil

from process_closer.models import CloseResult, ProcessRef, Target


class ProcessScanner:
    def __init__(self) -> None:
        self._pid = os.getpid()
        self._owner = psutil.Process(self._pid).username().casefold()
        self._hash_cache: dict[tuple[str, int, int], str | None] = {}
        self._publisher_cache: dict[tuple[str, int, int], str | None] = {}

    def find(self, target: Target) -> list[ProcessRef]:
        found: list[ProcessRef] = []
        attrs = ("pid", "name", "create_time", "username")
        for process in psutil.process_iter(attrs):
            try:
                info = process.info
                name = info["name"]
                owner = info["username"]
                if (
                    info["pid"] != self._pid
                    and name
                    and owner
                    and (target.key is None or name.casefold() == target.key)
                    and owner.casefold() == self._owner
                    and self._matches_filters(process, target)
                ):
                    found.append(ProcessRef(info["pid"], name, info["create_time"]))
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
        return found

    def _matches_filters(self, process: psutil.Process, target: Target) -> bool:
        if not target.path and not target.sha256 and not target.publisher:
            return True
        try:
            executable = os.path.normcase(os.path.abspath(process.exe()))
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return False
        if target.path and executable != target.path:
            return False
        if target.sha256 and self._file_hash(executable) != target.sha256:
            return False
        return not target.publisher or self._publisher(executable, target.publisher)

    def _file_hash(self, path: str) -> str | None:
        key = self._file_key(path)
        if key in self._hash_cache:
            return self._hash_cache[key]
        try:
            with open(path, "rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError:
            digest = None
        self._hash_cache[key] = digest
        return digest

    def _publisher(self, path: str, expected: str) -> bool:
        key = self._file_key(path)
        subject = self._publisher_cache.get(key)
        if key not in self._publisher_cache:
            subject = self._read_publisher(path)
            self._publisher_cache[key] = subject
        return bool(subject and expected.casefold() in subject.casefold())

    def _read_publisher(self, path: str) -> str | None:
        if os.name != "nt":
            return None
        command = (
            "$certificate = (Get-AuthenticodeSignature -LiteralPath $args[0]).SignerCertificate; "
            "if ($certificate) { $certificate.Subject }"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command, path],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.strip() or None

    def _file_key(self, path: str) -> tuple[str, int, int]:
        try:
            stat = os.stat(path)
            return path, stat.st_mtime_ns, stat.st_size
        except OSError:
            return path, 0, 0


class ProcessCloser:
    def __init__(self, timeout: float) -> None:
        self._timeout = timeout

    def close(self, refs: Iterable[ProcessRef]) -> list[CloseResult]:
        refs = list(refs)
        pending: list[tuple[ProcessRef, psutil.Process]] = []
        results: list[CloseResult] = []
        for ref in refs:
            try:
                process = psutil.Process(ref.pid)
                if process.create_time() != ref.started_at:
                    result = CloseResult(ref, False, reason="идентификатор процесса изменился")
                    results.append(result)
                    continue
                process.terminate()
                pending.append((ref, process))
            except psutil.NoSuchProcess:
                results.append(CloseResult(ref, True))
            except psutil.AccessDenied:
                results.append(CloseResult(ref, False, reason="недостаточно прав"))

        alive = self._wait(pending)
        survivors: list[tuple[ProcessRef, psutil.Process]] = []
        for ref, process in pending:
            if process.pid not in alive:
                results.append(CloseResult(ref, True))
                continue
            try:
                if process.create_time() != ref.started_at:
                    result = CloseResult(ref, False, reason="идентификатор процесса изменился")
                    results.append(result)
                    continue
                process.kill()
                survivors.append((ref, process))
            except psutil.NoSuchProcess:
                results.append(CloseResult(ref, True))
            except psutil.AccessDenied:
                results.append(CloseResult(ref, False, reason="недостаточно прав"))

        alive = self._wait(survivors)
        for ref, process in survivors:
            closed = process.pid not in alive
            reason = None if closed else "процесс не завершился"
            results.append(CloseResult(ref, closed, forced=True, reason=reason))
        return sorted(results, key=lambda item: item.process.pid)

    def _wait(self, items: list[tuple[ProcessRef, psutil.Process]]) -> set[int]:
        if not items:
            return set()
        processes = [process for _, process in items]
        try:
            _, alive = psutil.wait_procs(processes, timeout=self._timeout)
            return {process.pid for process in alive}
        except psutil.AccessDenied:
            return self._wait_by_pid(processes)

    def _wait_by_pid(self, processes: list[psutil.Process]) -> set[int]:
        alive = {process.pid for process in processes}
        deadline = time.monotonic() + self._timeout
        while alive:
            alive = {pid for pid in alive if psutil.pid_exists(pid)}
            remaining = deadline - time.monotonic()
            if not alive or remaining <= 0:
                return alive
            time.sleep(min(0.05, remaining))
        return alive
