@echo off
setlocal
cd /d %~dp0

echo ========================================
echo Reverse Solitaire - Single EXE Builder
echo ========================================

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3.10 or later is required to build the EXE.
        exit /b 1
    )
    set "PY=python"
)

%PY% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller is not installed. Installing build dependency...
    %PY% -m pip install "pyinstaller>=6,<7"
    if errorlevel 1 exit /b 1
)

echo.
echo Building a portable single-file Windows EXE...
if exist dist\ReverseSolitaire.exe del /q dist\ReverseSolitaire.exe

%PY% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name ReverseSolitaire ^
    --distpath dist ^
    --workpath build\pyinstaller ^
    --specpath build ^
    src\reverse_solitaire\app_v018.py

if errorlevel 1 (
    echo.
    echo [ERROR] EXE build failed.
    exit /b 1
)

echo.
echo ========================================
echo Build complete:
echo   %CD%\dist\ReverseSolitaire.exe
echo.
echo Only ReverseSolitaire.exe needs to be copied to another Windows PC.
echo Python does not need to be installed on the destination PC.
echo ========================================
endlocal
