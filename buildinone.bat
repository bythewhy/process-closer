@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%~fD\python.exe" set "PYTHON_EXE=%%~fD\python.exe"
)
if defined PYTHON_EXE goto use_exe
echo Python 3 не найден. Установите Python и повторите сборку.
popd
exit /b 1

:use_py
py -3 tools\build_single.py
goto finish

:use_python
python tools\build_single.py
goto finish

:use_exe
"%PYTHON_EXE%" tools\build_single.py

:finish
set "BUILD_CODE=%ERRORLEVEL%"
popd
exit /b %BUILD_CODE%
