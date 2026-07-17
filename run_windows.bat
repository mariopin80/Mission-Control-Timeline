@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Preparando o ambiente do Mission Pass Timeline...
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
    if errorlevel 1 goto :python_version
    py -3 -m venv .venv
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto :python_version
".venv\Scripts\python.exe" "src\main.py"
exit /b %errorlevel%

:python_version
echo.
echo Este programa requer Python 3.10 ou mais recente.
pause
exit /b 1

:error
echo.
echo Nao foi possivel preparar o programa.
echo Verifique se o Python 3 esta instalado e conectado a internet.
pause
exit /b 1
