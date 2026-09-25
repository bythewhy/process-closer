# Process Closer

Небольшая CLI-утилита, которая следит за выбранным приложением и завершает его,
как только процесс появляется в системе. Подходит для локальных сценариев, где
конкретная программа не должна оставаться запущенной.

Утилита сравнивает точное имя процесса без учёта регистра. Сначала она просит
процесс завершиться штатно, ждёт заданное время и только после этого использует
принудительное завершение. Перед каждым действием сверяются PID и время запуска,
поэтому переиспользованный системой PID не станет случайной целью. Монитор видит
только процессы текущего пользователя и никогда не завершает сам себя.

## Требования

- Python 3.11 или новее
- Windows, Linux или macOS
- права на завершение выбранного процесса

## Установка

```powershell
git clone https://github.com/neverlos3/prosecc-closer.git
cd prosecc-closer
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

Для Linux и macOS команда активации окружения выглядит так:

```bash
source .venv/bin/activate
```

## Использование

Запуск напрямую из корня репозитория:

```powershell
python main.py discord.exe
```

Если `.py`-файлы уже связаны с Python в Windows:

```powershell
main.py discord.exe
```

После установки пакета доступна короткая команда:

```powershell
process-closer discord.exe
```

В Windows расширение `.exe` можно не указывать:

```powershell
process-closer discord
```

По умолчанию проверка выполняется каждые 500 мс. Интервал и время ожидания
штатного завершения настраиваются отдельно:

```powershell
process-closer discord.exe --interval 0.2 --timeout 5
```

Чтобы проверить процессы один раз и сразу выйти:

```powershell
process-closer discord.exe --once
```

Дополнительные фильтры можно комбинировать. Все указанные условия должны
совпасть, иначе процесс не будет завершён:

```powershell
process-closer --path "C:\Tools\RedLotus\RedLotusAltChecker.exe"
process-closer RedLotusAltChecker.exe --path "C:\Tools\RedLotus\RedLotusAltChecker.exe"
process-closer --path "C:\Tools\RedLotus\RedLotusAltChecker.exe" `
    --sha256 "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
process-closer --path "C:\Tools\RedLotus\RedLotusAltChecker.exe" `
    --publisher "Red Lotus Software"
```

`--path` сравнивает нормализованный полный путь. `--sha256` проверяет содержимое
файла перед завершением и поэтому меняется после обновления приложения.
`--publisher` проверяет издателя сертификата Authenticode через PowerShell и
доступен на Windows. Фильтры можно использовать без позиционного имени процесса.

В Windows `--hide` запускает отдельный фоновый экземпляр через `pythonw.exe`,
возвращает приглашение командной строки и убирает окно консоли. При запуске уже
через `pythonw.exe` параметр просто оставляет монитор в фоне:

```powershell
main.py discord.exe --hide
```

Параметр `--hide` не скрывает процесс от операционной системы и не отключает
системный аудит. Ошибки фонового процесса не показываются в консоли; для отладки
используйте обычный запуск без `--hide`.

Остановить постоянный мониторинг можно сочетанием `Ctrl+C`.

## Автоперезапуск через Планировщик задач Windows

Установите дополнительную зависимость и зарегистрируйте задачу явно:

```powershell
python -m pip install -e ".[task]"
main.py --install-task Discord.exe --hide
```

В задачу попадут те же фильтры, которые указаны при регистрации:

```powershell
main.py --install-task --path "C:\Tools\Discord\Discord.exe" --publisher "Discord Inc" --hide
```

Задача запускается при входе пользователя и перезапускается Планировщиком после
сбоя с интервалом в одну минуту, максимум десять раз. Она не отключает аудит и
видна в Планировщике под именем `Process Closer`.

Удаление задачи:

```powershell
main.py --remove-task
```

## Сборка для Windows

Чтобы приложение отображалось под собственным именем вместо `python.exe`, его
можно собрать в обычный исполняемый файл:

```powershell
python -m pip install -e ".[build]"
pyinstaller --clean --noconfirm --name process-closer --paths src src/process_closer/launcher.py
```

Готовая сборка появится в `dist/process-closer/`. Она не скрыта от системы и не
отключает стандартный аудит запуска и завершения процессов.

Полный локальный релиз можно собрать одним скриптом:

```powershell
python -m pip install -e ".[build]"
powershell -ExecutionPolicy Bypass -File tools\build_release.ps1
```

Скрипт создаёт папку и ZIP в `release/`. Внутри будут `.exe`, `main.py`, README,
описание выпуска и лицензия.

## Один Python-файл

Запустите сборщик из корня проекта:

```powershell
buildinone.bat
```

Он объединит рабочие части проекта в `dist/process_closer.py`. Для запуска этого
файла пользователю нужны Python 3.11 или новее и библиотека `psutil`:

```powershell
python -m pip install "psutil>=6.1,<8"
python dist\process_closer.py discord.exe
```

`application.py` является внутренним модулем и отдельно не запускается. Для
обычного запуска используйте корневой `main.py`, а для распространения одного
файла — результат работы `buildinone.bat`.

## Ограничения

Process Closer не обходит модель прав операционной системы. Если целевой процесс
запущен с повышенными правами или от имени другого пользователя, утилити тоже
могут потребоваться соответствующие права. Завершение критичных системных
процессов заблокировано намеренно.

Программа не внедряется в другие процессы, не создаёт дампы и не записывает
историю запусков. При этом гарантировать отсутствие любых следов невозможно:
операционная система и средства аудита могут журналировать запуск и завершение
процессов.

## Разработка

```powershell
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Лицензия

[Apache License 2.0](LICENSE)

История и состав текущего выпуска описаны в [RELEASE.md](RELEASE.md).
