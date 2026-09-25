import sys
from importlib import import_module
from pathlib import Path


def configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def load_application():
    source = Path(__file__).resolve().parent / "src"
    sys.path.insert(0, str(source))
    try:
        return import_module("process_closer.application")
    except ModuleNotFoundError as error:
        if error.name == "psutil":
            print(
                "Не установлена библиотека psutil. Выполните: pip install psutil",
                file=sys.stderr,
            )
            raise SystemExit(1) from error
        raise


configure_output()
application = load_application()
raise SystemExit(application.run())
