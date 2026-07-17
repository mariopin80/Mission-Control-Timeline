@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv-build\Scripts\python.exe" (
    echo Criando ambiente de compilacao...
    py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
    if errorlevel 1 goto :python_version
    py -3 -m venv .venv-build
    if errorlevel 1 goto :error
)

".venv-build\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto :python_version
".venv-build\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv-build\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo Gerando executavel independente...
".venv-build\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name MissionPassTimeline ^
    --paths src ^
    --collect-all sgp4 ^
    src\main.py
if errorlevel 1 goto :error

echo.
echo Compilacao concluida:
echo %CD%\dist\MissionPassTimeline.exe
pause
exit /b 0

:python_version
echo.
echo A compilacao requer Python 3.10 ou mais recente.
pause
exit /b 1

:error
echo.
echo Falha na compilacao.
pause
exit /b 1
