@echo off
:: FIRE Video Processing Toolkit - Windows launcher
:: Usage: run.bat <command> [options]

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo ERROR: Virtual environment not found.
    echo Run setup first:  setup.bat
    echo Interactive script that detects Python and asks if you want GUI support.
    exit /b 1
)

set "COMMAND=%~1"

if "%COMMAND%"=="gui" (
    "%PYTHON%" "%SCRIPT_DIR%video_timestamp_recorder.py"
    goto :EOF
)

if "%COMMAND%"=="download" (
    "%PYTHON%" "%SCRIPT_DIR%firetimer-ytdownload.py" %2 %3 %4 %5 %6 %7 %8 %9
    goto :EOF
)

if "%COMMAND%"=="cut" (
    "%PYTHON%" "%SCRIPT_DIR%firetimer-cutvid.py" %2 %3 %4 %5 %6 %7 %8 %9
    goto :EOF
)

if "%COMMAND%"=="join" (
    "%PYTHON%" "%SCRIPT_DIR%firetimer-joinvids.py" %2 %3 %4 %5 %6 %7 %8 %9
    goto :EOF
)

if "%COMMAND%"=="timer" (
    "%PYTHON%" "%SCRIPT_DIR%add-timer.py" %2 %3 %4 %5 %6 %7 %8 %9
    goto :EOF
)

echo FIRE Video Processing Toolkit
echo.
echo Usage: run.bat ^<command^> [options]
echo.
echo Commands:
echo   gui                                     Launch GUI timestamp recorder
echo   download -u ^<URL^> -n ^<name^> [options]   Download YouTube video
echo   cut -s ^<video.mp4^> -t ^<timestamps.txt^>  Cut video by timestamps
echo   join --parts ^<folder^> [--out file.mp4]  Join video parts
echo   timer -s ^<video.mp4^> [options]          Add timer overlay to video
echo.
echo Examples:
echo   run.bat download -u https://youtube.com/watch?v=xyz -n myvideo
echo   run.bat download -u https://youtube.com/watch?v=xyz -n myvideo -f myfolder -c 10
echo   run.bat cut -s myvideo.mp4 -t timestamps.txt
echo   run.bat timer -s myvideo.mp4 --start 00:00:05.000 --end 00:00:20.000
echo   run.bat timer -s myvideo.mp4 --start 00:00:05.000 --end-relative 00:00:15.000
echo   run.bat timer -s myvideo.mp4 --start 00:00:05.000 --end 00:00:20.000 -o out.mp4
echo.
echo Pass --help to any command for full options, e.g.:
echo   run.bat download --help
echo   run.bat cut --help

if not "%COMMAND%"=="" (
    echo.
    echo Unknown command: %COMMAND%
    exit /b 1
)
