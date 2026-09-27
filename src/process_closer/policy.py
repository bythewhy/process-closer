import os
import re
from pathlib import PurePath

from process_closer.errors import InvalidTargetError
from process_closer.models import Target


class TargetPolicy:
    _protected = {
        "csrss.exe",
        "dwm.exe",
        "explorer.exe",
        "fontdrvhost.exe",
        "lsass.exe",
        "registry",
        "services.exe",
        "smss.exe",
        "svchost.exe",
        "system",
        "system idle process",
        "wininit.exe",
        "winlogon.exe",
    }

    def create(
        self,
        value: str | None = None,
        path: str | None = None,
        sha256: str | None = None,
        publisher: str | None = None,
        copyright: str | None = None,
    ) -> Target:
        if not value and not path and not sha256 and not publisher and not copyright:
            raise InvalidTargetError(
                "укажите имя процесса, --path или хотя бы один фильтр"
            )
        name = (
            self._name(value)
            if value
            else self._name(PurePath(path).name)
            if path
            else None
        )
        target_path = self._path(path) if path else None
        digest = sha256.casefold() if sha256 else None
        if digest and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise InvalidTargetError("--sha256 должен содержать 64 шестнадцатеричных символа")
        owner = publisher.strip() if publisher else None
        if publisher is not None and not owner:
            raise InvalidTargetError("--publisher не может быть пустым")
        rights = copyright.strip() if copyright else None
        if copyright is not None and not rights:
            raise InvalidTargetError("--copyright не может быть пустым")
        target = Target(name, target_path, digest, owner, rights)
        if target.key in self._protected:
            raise InvalidTargetError(f"нельзя выбрать защищённый процесс: {target.name}")
        return target

    def _name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise InvalidTargetError("имя процесса не может быть пустым")
        if name != PurePath(name).name or "/" in name or "\\" in name:
            raise InvalidTargetError("укажите имя процесса, а не путь к файлу")
        if name in {".", ".."} or "\x00" in name:
            raise InvalidTargetError("некорректное имя процесса")
        if os.name == "nt" and "." not in name:
            return f"{name}.exe"
        return name

    def _path(self, value: str) -> str:
        raw = os.path.expanduser(value.strip())
        if not os.path.isabs(raw):
            raise InvalidTargetError("--path должен быть абсолютным путём")
        if "\x00" in raw:
            raise InvalidTargetError("--path содержит недопустимый символ")
        path = os.path.abspath(raw)
        return os.path.normcase(path)
