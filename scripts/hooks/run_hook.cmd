@echo off
REM Athanor native Windows hook launcher.
REM Usage: run_hook.cmd "<abs path to hook .py>"
REM Invoked from command_windows; Codex runs Windows hook commands via cmd.exe.
REM Probes read from NUL so the hook JSON payload stays available to target.

setlocal
set "TARGET=%~1"
if "%TARGET%"=="" (
  echo athanor run_hook.cmd: missing target hook script argument 1>&2
  exit /B 1
)

set "PROBE=import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"

py -3 -c "%PROBE%" < NUL > NUL 2> NUL
if not errorlevel 1 goto run_py_launcher

python -c "%PROBE%" < NUL > NUL 2> NUL
if not errorlevel 1 goto run_python

python3 -c "%PROBE%" < NUL > NUL 2> NUL
if not errorlevel 1 goto run_python3

echo athanor hook gate INACTIVE: no working Python >= 3.10 on PATH (tried: py -3, python, python3). Active hooks (kernel guard, evidence sniffer) did NOT run. Install Python 3.10+ (https://www.python.org/downloads/). 1>&2
exit /B 1

:run_py_launcher
py -3 "%TARGET%"
exit /B %ERRORLEVEL%

:run_python
python "%TARGET%"
exit /B %ERRORLEVEL%

:run_python3
python3 "%TARGET%"
exit /B %ERRORLEVEL%
