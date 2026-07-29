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

echo Gerando distribuicao em pasta...
".venv-build\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --noupx ^
    --name MissionControlTimeline ^
    --paths src ^
    --collect-all sgp4 ^
    --add-data "assets\mission-control-timeline.ico;assets" ^
    --add-data "assets\mission-control-timeline-about.png;assets" ^
    --icon assets\mission-control-timeline.ico ^
    --version-file packaging\windows_version_info.txt ^
    src\main.py
if errorlevel 1 goto :error

echo.
echo Aplicacao gerada:
echo %CD%\dist\MissionControlTimeline\MissionControlTimeline.exe

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if defined ISCC (
    echo.
    echo Gerando instalador com Inno Setup...
    "%ISCC%" "packaging\MissionControlTimeline.iss"
    if errorlevel 1 goto :error
    echo.
    echo Instalador concluido:
    echo %CD%\dist-installer\MissionControlTimeline_Setup_0.8.1.exe
) else (
    echo.
    echo Inno Setup 6 nao encontrado. A pasta do aplicativo foi gerada normalmente.
    echo Para criar o instalador, instale o Inno Setup e execute este arquivo novamente.
)
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
