@echo off
REM Activate the virtual environment for all commands
set VENV_PATH=%~dp0..\.venv
set PYTHON=%VENV_PATH%\Scripts\python.exe
set CELERY=%VENV_PATH%\Scripts\celery.exe

REM === Start Django server ===
echo Starting Django server...
start cmd /k "%PYTHON% -m daphne -b 0.0.0.0 -p 8000 backend.asgi:application


REM === Start Celery worker ===
echo Starting Celery worker...
start cmd /k "%CELERY% -A backend worker --loglevel=info"

REM === (Optional) Start Celery beat for scheduled tasks ===
REM echo Starting Celery beat...
REM start cmd /k "%CELERY% -A backend beat --loglevel=info"

REM === (Optional) Start Daphne server for Channels (if not using runserver) ===
REM echo Starting Daphne server...
REM start cmd /k "%PYTHON% -m daphne -b 0.0.0.0 -p 8001 backend.asgi:application"