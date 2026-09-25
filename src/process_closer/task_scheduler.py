import os
import shutil
import subprocess
import sys
from pathlib import Path

from process_closer.errors import TaskSchedulerError


class TaskScheduler:
    name = "Process Closer"

    def install(self, arguments: list[str]) -> None:
        try:
            import win32com.client
        except ImportError as error:
            raise TaskSchedulerError(
                "для регистрации задачи установите зависимость: pip install pywin32"
            ) from error

        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.is_file():
            located = shutil.which("pythonw.exe")
            if not located:
                raise TaskSchedulerError("pythonw.exe не найден")
            pythonw = Path(located)

        script = Path(__file__).resolve().parents[2] / "main.py"
        if not script.is_file():
            raise TaskSchedulerError(f"не найден файл запуска: {script}")

        child_args = [item for item in arguments if item != "--install-task"]
        if "--hide" not in child_args:
            child_args.append("--hide")
        if "--once" in child_args:
            raise TaskSchedulerError("нельзя регистрировать задачу с параметром --once")

        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        folder = scheduler.GetFolder("\\")
        definition = scheduler.NewTask(0)
        definition.RegistrationInfo.Description = "Фоновый монитор Process Closer"

        trigger = definition.Triggers.Create(9)
        trigger.UserId = os.environ.get("USERNAME")

        action = definition.Actions.Create(0)
        action.Path = str(pythonw)
        action.Arguments = subprocess.list2cmdline([str(script), *child_args])
        action.WorkingDirectory = str(script.parent)

        settings = definition.Settings
        settings.Enabled = True
        settings.StartWhenAvailable = True
        settings.RestartCount = 10
        settings.RestartInterval = "PT1M"
        settings.ExecutionTimeLimit = "PT0S"

        folder.RegisterTaskDefinition(
            self.name,
            definition,
            6,
            None,
            None,
            3,
        )

    def remove(self) -> None:
        try:
            import win32com.client
        except ImportError as error:
            raise TaskSchedulerError(
                "для удаления задачи установите зависимость: pip install pywin32"
            ) from error

        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()
        folder = scheduler.GetFolder("\\")
        try:
            folder.DeleteTask(self.name, 0)
        except Exception as error:
            raise TaskSchedulerError(f"не удалось удалить задачу «{self.name}»") from error
