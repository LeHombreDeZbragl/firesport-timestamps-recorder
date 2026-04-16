@echo off
REM FIRE Video Processing Toolkit - Windows setup script
REM Automatically calls install.py with correct Python executable

setlocal enabledelayedexpansion

REM Try to find Python (python command should be on PATH)
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.8+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)

echo Checking Python version...
python --version

echo.
echo FIRE Video Processing Toolkit Setup
echo ====================================
echo.

REM Ask user if they want GUI
set /p GUI="Do you want to install GUI support? (y/n, default=n): "
if /i "%GUI%"=="y" (
    echo Running: python install.py --gui
    python install.py --gui
) else (
    echo Running: python install.py
    python install.py
)

if errorlevel 1 (
    echo.
    echo Setup failed. Check the errors above.
    exit /b 1
)

echo.
echo Setup complete!
echo.
echo To use FIRE:
echo   run.bat help              - Show all commands
echo   run.bat download -u ^<URL^> -n ^<name^>  - Download YouTube video
echo   run.bat gui                - Record timestamps (requires FFmpeg + VLC)
echo   run.bat cut -s video.mp4 -t timestamps.txt - Cut video by timestamps
echo.
pause
