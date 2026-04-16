#!/usr/bin/env python3
"""
Cross-platform setup script for FIRE Video Processing Toolkit.

Usage:
  python3 install.py          # CLI tools only (download, cut, join, timer)
  python3 install.py --gui    # CLI + GUI (video_timestamp_recorder.py)
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys


def _ok(msg):
    print(f"  OK  {msg}")


def _warn(msg):
    print(f"  WARN  {msg}")


def _fail(msg):
    print(f"  ERROR  {msg}")


def check_python():
    if sys.version_info < (3, 8):
        _fail(f"Python 3.8+ required. You have {sys.version}")
        sys.exit(1)
    _ok(f"Python {sys.version.split()[0]}")


def _ffmpeg_hint():
    os_name = platform.system()
    if os_name == "Windows":
        print("         https://ffmpeg.org/download.html")
        print("         Or via Chocolatey: choco install ffmpeg")
    elif os_name == "Darwin":
        print("         brew install ffmpeg")
    else:
        print("         sudo apt-get install ffmpeg")


def _vlc_hint():
    os_name = platform.system()
    if os_name == "Windows":
        print("         https://www.videolan.org/")
        print("         Or via Chocolatey: choco install vlc")
    elif os_name == "Darwin":
        print("         brew install --cask vlc")
    else:
        print("         sudo apt-get install vlc")


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        _fail("FFmpeg not found. Install it:")
        _ffmpeg_hint()
        sys.exit(1)
    _ok("FFmpeg found")


def check_vlc():
    if shutil.which("vlc") is None:
        _warn("VLC not found (required for GUI). Install it:")
        _vlc_hint()
        return False
    _ok("VLC found")
    return True


def create_venv():
    if os.path.exists("venv"):
        _ok("Virtual environment already exists")
        return
    print("  Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    _ok("Virtual environment created")


def _venv_python():
    if platform.system() == "Windows":
        return os.path.join("venv", "Scripts", "python.exe")
    return os.path.join("venv", "bin", "python3")


def install_deps(gui=False):
    python = _venv_python()
    reqs = "requirements_gui.txt" if gui else "requirements.txt"
    label = "CLI + GUI" if gui else "CLI"
    print(f"  Installing {label} dependencies...")
    subprocess.run(
        [python, "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True
    )
    subprocess.run([python, "-m", "pip", "install", "-r", reqs], check=True)
    _ok("Dependencies installed")


def print_next_steps(gui=False):
    os_name = platform.system()
    print()
    print("Setup complete!")
    print()
    print("Activate environment:")
    if os_name == "Windows":
        print(r"  venv\Scripts\activate")
    else:
        print("  source venv/bin/activate")
    print()
    print("Or use the launcher scripts directly:")
    if os_name == "Windows":
        print("  run.bat download -u <URL> -n <name>")
        print("  run.bat cut -s video.mp4 -t timestamps.txt")
        if gui:
            print("  run.bat gui")
    else:
        print("  ./run.sh download -u <URL> -n <name>")
        print("  ./run.sh cut -s video.mp4 -t timestamps.txt")
        if gui:
            print("  ./run.sh gui")
    print()
    print("Or use the Makefile (Linux/macOS only):")
    print("  make help")


def main():
    parser = argparse.ArgumentParser(
        description="Set up FIRE Video Processing environment"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Also install GUI dependencies (PyQt5, python-vlc). Requires VLC on system.",
    )
    args = parser.parse_args()

    print("FIRE Video Processing Toolkit - Setup")
    print("=" * 40)
    print("Checking requirements...")
    check_python()
    check_ffmpeg()
    if args.gui:
        check_vlc()
    create_venv()
    install_deps(gui=args.gui)
    print_next_steps(gui=args.gui)


if __name__ == "__main__":
    main()
