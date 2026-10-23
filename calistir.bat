@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe ( echo once kur.ps1 calistir & exit /b 1 )
if "%PORT%"=="" set PORT=8095
echo Gateway baslatiliyor -> 0.0.0.0:%PORT%  (Ctrl+C ile durdur)
venv\Scripts\python -m uvicorn gateway:app --host 0.0.0.0 --port %PORT%
