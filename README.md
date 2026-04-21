FIRE - Video Processing Toolkit
=================================

Four tools for recording timestamps, downloading YouTube videos, cutting/joining video segments with overlays.

**Tools:**
- `firetimer-ytdownload.py` — Download YouTube videos
- `video_timestamp_recorder.py` — GUI for frame-accurate timestamps
- `firetimer-cutvid.py` — Cut by timestamps, add title+timer overlays
- `firetimer-joinvids.py` — Fast FFmpeg concat joiner
- `add-timer.py` — Add a running timer overlay to any video

**Known issues:**
- `firetimer-ytdownload.py` on *Windows* is not working reliably.
- Some overlay diacritics may not render correctly on *Linux*.
- `video_timestamp_recorder.py` has sound problems on *Linux*.
- *Linux* tested only in ubuntu WSL2.0.
- *MacOS* not tested.

Setup
-----

### Step 0: Install Python (if not already installed)

**Minimum required: Python 3.8**  
**Recommended: Python 3.13** (see `.python-version`)

#### Windows

1. Download from [python.org](https://www.python.org/downloads/) → get latest 3.13 or 3.12
2. **Important:** Check "Add Python to PATH" during installation
3. Restart your terminal
4. Verify: Open Windows CMD and type:
   ```bat
   python --version
   ```

#### Linux

Usually pre-installed. If not:
```bash
sudo apt-get install python3 python3-venv
```

#### macOS

```bash
brew install python3
```

### Step 1: Install system dependencies

**FFmpeg** (required by all tools):

| OS | Command |
|----|---------|
| Linux | `sudo apt-get install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Windows | `choco install ffmpeg` or [download](https://ffmpeg.org/download.html) |

**VLC** (required only for GUI recorder):

| OS | Command |
|----|---------|
| Linux | `sudo apt-get install vlc` |
| macOS | `brew install --cask vlc` |
| Windows | `choco install vlc` or [download](https://www.videolan.org/) |

### Step 2: Set up Python environment

**Windows:**
Make sure you are running this in admin CMD or PowerShell.

```bat
setup.bat
```
*Interactive script that detects Python and asks if you want GUI support.*

**Linux/macOS:**

Automated:
```bash
python3 install.py          # CLI only
python3 install.py --gui    # CLI + GUI
```

With Makefile:
```bash
make setup
```

**All platforms - Manual:**
```bash
python3 -m venv venv

source venv/bin/activate                 # Linux/macOS
venv\Scripts\activate                    # Windows

pip install -r requirements.txt          # CLI only
pip install -r requirements_gui.txt      # CLI + GUI
```

Quick Start
-----------

Choose your preferred interface. All three methods do the same thing.

### Makefile (Linux/macOS)

```bash
# Show all available commands
make help

# Workflow: download → record → cut → output
make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo
make gui
# Load myvideo.mp4 → mark starts/ends → export timestamps.txt
make cut SOURCE=myvideo.mp4 TIMES=timestamps.txt
# Output: out-parts/ folder + final_myvideo.mp4

# Individual commands:
make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo                            
# Download video
make download URL='https://youtube.com/watch?v=xyz' NAME=myvideo FOLDER=myfolder CHUNK=10   
# Download to folder, 10min chunks
make gui                                                                                     
# Record timestamps (GUI)
make cut SOURCE=video.mp4 TIMES=timestamps.txt                                              
# Cut by timestamps
make cut SOURCE=video.mp4 TIMES=timestamps.txt SORT=1                                       
# Cut + sort by time
make join FOLDER=path/to/parts OUTPUT=final.mp4                                             
# Join parts
make timer SOURCE=video.mp4                                                                 
# Add timer overlay
make timer SOURCE=video.mp4 START=00:00:05.000 END=00:00:20.000                            
# Timer with time range
make timer SOURCE=video.mp4 START=00:00:05.000 END_REL=00:00:15.000                        
# Timer with relative end
make timer SOURCE=video.mp4 START=00:00:05.000 END=00:00:20.000 OUTPUT=out.mp4             
# Timer with custom output
```

---

### Windows (run.bat)

```bat
REM Show help
run.bat

REM NOTE: The download command has known issues on Windows and may not work reliably.
REM       Consider using yt-dlp directly or downloading via a browser extension instead.
REM Workflow: download → record → cut → output
run.bat download -u https://youtube.com/watch?v=xyz -n myvideo
run.bat gui
REM Load myvideo.mp4 → mark starts/ends → export timestamps.txt
run.bat cut -s myvideo.mp4 -t timestamps.txt
REM Output: out-parts\ folder + final_myvideo.mp4

REM Individual commands:
run.bat download -u "https://youtube.com/watch?v=xyz" -n myvideo                       
REM Download video
run.bat download -u "https://youtube.com/watch?v=xyz" -n myvideo -f myfolder -c 10     
REM Download to folder, 10min chunks
run.bat gui                                                                           
REM Record timestamps (GUI)
run.bat cut -s video.mp4 -t timestamps.txt                                            
REM Cut by timestamps
run.bat cut -s video.mp4 -t timestamps-muzi.txt,timestamps-zeny.txt                  
REM Cut with multiple timestamp files (comma-delimited)
run.bat cut -s video.mp4 -t timestamps.txt -z                                         
REM Cut + sort by time
run.bat join --parts path\to\parts --out final.mp4                                    
REM Join parts
run.bat timer -s video.mp4                                                            
REM Add timer overlay
run.bat timer -s video.mp4 --start 00:00:05.000 --end 00:00:20.000                   
REM Timer with time range
run.bat timer -s video.mp4 --start 00:00:05.000 --end-relative 00:00:15.000          
REM Timer with relative end
run.bat timer -s video.mp4 --start 00:00:05.000 --end 00:00:20.000 -o out.mp4        
REM Timer with custom output
```

---

### Direct Python (All platforms)

```bash

# Workflow: download → record → cut → output
python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n myvideo
python3 video_timestamp_recorder.py
# Load myvideo.mp4 → mark starts/ends → export timestamps.txt
python3 firetimer-cutvid.py -s myvideo.mp4 -t timestamps.txt
# Output: out-parts/ folder + final_myvideo.mp4

# Individual commands:
python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n myvideo                    
# Download video
python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n myvideo -f myfolder -c 10  
# Download to folder, 10min chunks
python3 video_timestamp_recorder.py                                                               
# Record timestamps (GUI)
python3 firetimer-cutvid.py -s video.mp4 -t timestamps.txt                                       
# Cut by timestamps
python3 firetimer-cutvid.py -s video.mp4 -t timestamps-muzi.txt,timestamps-zeny.txt              
# Cut with multiple timestamp files (comma-delimited)
python3 firetimer-cutvid.py -s video.mp4 -t timestamps.txt -z                                    
# Cut + sort by time
python3 firetimer-joinvids.py --parts path/to/parts --out final.mp4                              
# Join parts
python3 add-timer.py -s video.mp4                                                                
# Add timer overlay
python3 add-timer.py -s video.mp4 --start 00:00:05.000 --end 00:00:20.000                       
# Timer with time range
python3 add-timer.py -s video.mp4 --start 00:00:05.000 --end-relative 00:00:15.000              
# Timer with relative end
python3 add-timer.py -s video.mp4 --start 00:00:05.000 --end 00:00:20.000 -o out.mp4            
# Timer with custom output
```

Timestamp File Format
---------------------
Each line has 12 fields (generated by video_timestamp_recorder.py):
`title;začátek;start;koš;voda;kohout;rozdělovač;výstřik_LP;výstřik_PP;LP;PP;konec`

```
Zbraslav;00:00:11.900;00:00:16.901;00:00:17.400;00:00:18.151;00:00:18.402;00:00:19.151;00:00:19.651;00:00:19.901;00:00:20.400;00:00:20.901;00:00:21.901
```

Lines starting with `#` are ignored.

GUI Recorder Shortcuts
-----------------------
| Key | Action |
|-----|--------|
| `Q` | Mark začátek (start) |
| `W-P` | Mark splits 1-9 |
| `[` | Mark konec (end) |
| `N` | Focus name field |
| `Space` | Play/pause |
| `,` / `.` | Frame ±1 |
| `Shift + ←/→` | Frame ±10 |

Options
-------
**YouTube Download:**
- `-u, --url` (required) — YouTube URL
- `-n, --name` (required) — filename/folder name (also default folder name)
- `-f, --folder` — output folder (default: uses `--name` as folder name)
- `-s, --start` / `-e, --end` — time range (minutes, MM:SS, or HH:MM:SS)
- `-c, --chunk-minutes` — chunk size (default: 120)

**Cut Video:**
- `-s, --source` (required) — video file
- `-t, --times` (required) — timestamps file(s), comma-delimited for multiple (e.g. `-t file1.txt,file2.txt`)
- `-z` — sort by final time (max of LP/PP) and add placement labels (1.místo, 2.místo, etc.)

**Join Video:**
- `-f, --folder, --parts` (required) — folder containing MP4 parts to join
- `-O, --out` — output filename (default: auto-generated based on folder type)

**Add Timer:**
- `-s, --source` (required) — input video file
- `--start` — absolute time when timer starts counting (default: 00:00:00.000)
- `--end` — absolute time when timer freezes (default: end of video)
- `--end-relative` — duration from `--start` when timer freezes (alternative to `--end`)
- `-o, --output` — output file (default: `<source_stem>_timer.mp4`)

Folder Structure
----------------
- `in-parts/` — downloaded input chunks
- `out-parts/` — processed output segments
- Joined video saves one level above parts folder

Troubleshooting
---------------
- **Python not found:** Make sure Python 3.8+ is installed and on your PATH (see Step 0 in Setup above)
  - Windows: Download from [python.org](https://www.python.org/), check "Add Python to PATH"
  - Linux: `sudo apt-get install python3`
  - macOS: `brew install python3`
- **python3 command not found:** Try only python. 
- **Python version mismatch:** Project recommends Python 3.13, but 3.8+ is supported. If you have 3.12, it will work fine.
- **FFmpeg not found:** See Step 1 above for install instructions per OS
- **VLC not found:** Required only for GUI — see Step 1 above
- **Download command fails with "unrecognized arguments":** On Windows, URLs with special characters (like dashes `-`) need to be quoted:
  - ❌ `run.bat download -u https://youtube.com/watch?v=-xyz -n video` (fails)
  - ✅ `run.bat download -u "https://youtube.com/watch?v=-xyz" -n video` (works)
- **yt-dlp JavaScript runtime warning:** You may see a warning about "No supported JavaScript runtime could be found" during downloads. This is harmless — downloads will still work. To eliminate the warning, install Node.js from [nodejs.org](https://nodejs.org/)
- **Run `--help` on any script** for detailed options (e.g. `python3 firetimer-cutvid.py --help` or `make cut --help`)

License
-------
MIT License - See [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Tomáš Buchta
