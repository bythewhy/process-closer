import argparse
import os
import subprocess
import sys
from pathlib import Path

from process_closer.errors import InvalidTargetError, TaskSchedulerError
from process_closer.models import CloseResult
from process_closer.monitor import ProcessMonitor
from process_closer.policy import TargetPolicy
from process_closer.processes import ProcessCloser, ProcessScanner
from process_closer.task_scheduler import TaskScheduler


class RussianHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading: str | None) -> None:
        headings = {
            "positional arguments": "позиционные аргументы",
            "optional arguments": "параметры",
            "options": "параметры",
        }
        super().start_section(headings.get(heading, heading))


class RussianArgumentParser(argparse.ArgumentParser):
    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "использование:", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "использование:", 1)

    def error(self, message: str) -> None:
        replacements = {
            "the following arguments are required:": "не указаны обязательные аргументы:",
            "unrecognized arguments:": "неизвестные аргументы:",
            "expected one argument": "ожидается одно значение",
            "argument ": "аргумент ",
        }
        for source, replacement in replacements.items():
            message = message.replace(source, replacement)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: ошибка: {message}\n")


def parse_seconds(value: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("ожидается число") from error


def configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def detach_if_requested(args: list[str]) -> bool:
    if os.name != "nt" or "--hide" not in args:
        return False
    if "--install-task" in args or "--remove-task" in args:
        return False
    if os.environ.get("PROCESS_CLOSER_BACKGROUND") == "1":
        return False
    if Path(sys.executable).name.casefold() == "pythonw.exe":
        return False

    if getattr(sys, "frozen", False):
        command = [sys.executable, *args]
    else:
        script = Path(sys.argv[0]).resolve()
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.is_file():
            return False
        if script.suffix.casefold() in {".py", ".pyw"}:
            command = [str(pythonw), str(script), *args]
        elif script.stem.casefold() == "process-closer":
            command = [str(pythonw), "-m", "process_closer.application", *args]
        else:
            return False

    environment = os.environ.copy()
    environment["PROCESS_CLOSER_BACKGROUND"] = "1"
    flags = 0x00000008 | 0x00000200 | 0x08000000
    subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
        env=environment,
    )
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = RussianArgumentParser(
        prog="process-closer",
        description="Завершает выбранное приложение сразу после его запуска.",
        formatter_class=RussianHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "process",
        nargs="?",
        metavar="ПРОЦЕСС",
        help="имя процесса, например discord.exe",
    )
    parser.add_argument("--path", metavar="ПУТЬ", help="полный путь к исполняемому файлу")
    parser.add_argument(
        "--sha256",
        metavar="ХЕШ",
        help="SHA-256 исполняемого файла: 64 шестнадцатеричных символа",
    )
    parser.add_argument(
        "--publisher",
        metavar="ИЗДАТЕЛЬ",
        help="часть имени издателя цифровой подписи Windows",
    )
    parser.add_argument(
        "--interval",
        type=parse_seconds,
        default=0.5,
        metavar="СЕКУНДЫ",
        help="интервал проверки от 0,1 до 60 секунд (по умолчанию: 0,5)",
    )
    parser.add_argument(
        "--timeout",
        type=parse_seconds,
        default=3.0,
        metavar="СЕКУНДЫ",
        help="ожидание завершения от 0 до 60 секунд (по умолчанию: 3)",
    )
    parser.add_argument("--once", action="store_true", help="проверить один раз и выйти")
    task_group = parser.add_mutually_exclusive_group()
    task_group.add_argument(
        "--install-task",
        action="store_true",
        help="зарегистрировать перезапуск монитора в Планировщике задач",
    )
    task_group.add_argument(
        "--remove-task",
        action="store_true",
        help="удалить задачу Process Closer из Планировщика",
    )
    parser.add_argument(
        "--hide",
        action="store_true",
        help="запустить фоновый монитор без окна консоли",
    )
    parser.add_argument("-h", "--help", action="help", help="показать справку и выйти")
    return parser


def run(argv: list[str] | None = None) -> int:
    configure_output()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if detach_if_requested(raw_args):
        return 0
    parser = build_parser()
    args = parser.parse_args(raw_args)
    scheduler = TaskScheduler()
    if args.remove_task:
        try:
            scheduler.remove()
        except TaskSchedulerError as error:
            parser.error(str(error))
        print("Задача Process Closer удалена")
        return 0
    if args.install_task:
        if args.once:
            parser.error("нельзя регистрировать задачу с параметром --once")
        try:
            TargetPolicy().create(args.process, args.path, args.sha256, args.publisher)
            scheduler.install(raw_args)
        except (InvalidTargetError, TaskSchedulerError) as error:
            parser.error(str(error))
        print("Задача Process Closer зарегистрирована")
        return 0
    if not 0.1 <= args.interval <= 60:
        parser.error("--interval должен быть от 0,1 до 60")
    if not 0 <= args.timeout <= 60:
        parser.error("--timeout должен быть от 0 до 60")
    try:
        target = TargetPolicy().create(args.process, args.path, args.sha256, args.publisher)
    except InvalidTargetError as error:
        parser.error(str(error))

    def report(result: CloseResult) -> None:
        if result.closed:
            if not args.hide:
                method = "завершён принудительно" if result.forced else "завершён"
                print(f"{result.process.name} (PID {result.process.pid}) {method}")
        else:
            message = (
                f"не удалось завершить {result.process.name} "
                f"(PID {result.process.pid}): {result.reason}"
            )
            print(
                message,
                file=sys.stderr,
            )

    monitor = ProcessMonitor(
        ProcessScanner(),
        ProcessCloser(args.timeout),
        args.interval,
        report,
    )
    if not args.hide:
        label = target.name or target.path
        print(f"Ожидание {label}. Для остановки нажмите Ctrl+C")
    try:
        monitor.run(target, once=args.once)
    except KeyboardInterrupt:
        monitor.stop()
        if not args.hide:
            print("Мониторинг остановлен")
    return 0
