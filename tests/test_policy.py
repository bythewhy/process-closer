import os

import pytest

from process_closer.errors import InvalidTargetError
from process_closer.policy import TargetPolicy


def test_accepts_executable_name() -> None:
    target = TargetPolicy().create("  Discord.exe  ")

    assert target.name == "Discord.exe"
    assert target.key == "discord.exe"


def test_adds_windows_extension() -> None:
    target = TargetPolicy().create("Discord")

    expected = "Discord.exe" if os.name == "nt" else "Discord"
    assert target.name == expected


@pytest.mark.parametrize("value", ["", "  ", "../app.exe", "dir/app.exe", "dir\\app.exe"])
def test_rejects_invalid_names(value: str) -> None:
    with pytest.raises(InvalidTargetError):
        TargetPolicy().create(value)


@pytest.mark.parametrize("value", ["lsass.exe", "SVCHOST.EXE", "explorer.exe"])
def test_rejects_protected_processes(value: str) -> None:
    with pytest.raises(InvalidTargetError):
        TargetPolicy().create(value)


def test_accepts_optional_filters() -> None:
    target = TargetPolicy().create(
        path=os.path.abspath("app.exe"),
        sha256="A" * 64,
        publisher="Example Corp",
    )

    assert target.name == "app.exe"
    assert target.path == os.path.normcase(os.path.abspath("app.exe"))
    assert target.sha256 == "a" * 64
    assert target.publisher == "Example Corp"


def test_requires_absolute_path() -> None:
    with pytest.raises(InvalidTargetError):
        TargetPolicy().create(path="app.exe")
