# FIRE - Video Processing Toolkit

**FIRE** is a comprehensive suite of Python tools for professional video processing workflows: recording precise timestamps with a GUI, downloading from YouTube in time-based chunks, cutting videos into segments with overlays, and joining multiple videos together.

---

## 🔥 Tools Overview

### 1. `video_timestamp_recorder.py` - GUI Timestamp Recorder
Interactive video player for recording timestamped segments with **frame-by-frame precision** and millisecond accuracy. Video-only operation (audio disabled for stability).

### 2. `firetimer-ytdownload.py` - YouTube Video Downloader
Downloads YouTube videos in time-based chunks with support for specific time ranges. Smart defaults make it easy to use.

### 3. `firetimer-cutvid.py` - Video Segment Cutter
Cuts videos into segments based on timestamps, adding title and timer overlays to each segment. Auto-joins segments into final video.

### 4. `firetimer-joinvids.py` - Video Joiner
Joins multiple MP4 files into a single video with optional intro/outro clips using fast stream copying.

---

## 📋 Requirements

### System Requirements
- **Python 3.8+**
- **[FFmpeg](https://ffmpeg.org/)** (must be in your PATH)
- **VLC Media Player** (for GUI timestamp recorder)

### Install Dependencies

```bash
# For command-line tools only
pip install -r requirements.txt

# For GUI timestamp recorder
pip install -r requirements_gui.txt
```

**requirements.txt:**
- yt-dlp

**requirements_gui.txt:**
- PyQt5>=5.15.0
- python-vlc>=3.0.0

---

## 🚀 Quick Start

### Complete Workflow Example

```bash
# Method 1: Process Local Video
# 1. Record timestamps using GUI
python3 video_timestamp_recorder.py
# Load video → mark segments → export timestamps.txt

# 2. Cut and join automatically
python3 firetimer-cutvid.py -s video.mp4 -t timestamps.txt
# Creates: out-parts/ folder + final_out_video.mp4

# Method 2: Process YouTube Video
# 1. Download (folder auto-generated from name)
python3 firetimer-ytdownload.py -u "https://youtube.com/watch?v=xyz" -n my_video
# Creates: my_video/ folder with in-parts/ + my_video.mp4

# 2. Download specific time range
python3 firetimer-ytdownload.py -u "URL" -n video -s 10:30 -e 45:20
# Downloads only 10:30 to 45:20
```

---

## 📖 Detailed Usage

### 🎬 Video Timestamp Recorder (GUI)

**Launch:**
```bash
python3 video_timestamp_recorder.py
```

#### Features
- ✅ Embedded video player with VLC backend
- ✅ Frame-by-frame navigation (comma/period keys)
- ✅ Millisecond precision timestamps
- ✅ Inline segment naming (no modal dialogs)
- ✅ Auto-generated segment names
- ✅ Live segment editing
- ✅ Export to `timestamps.txt`

#### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `S` | Save start timestamp |
| `E` | Save end timestamp |
| `N` | Focus segment name field |
| `Space` | Play/Pause |
| `,` (comma) | Back 1 frame |
| `.` (period) | Forward 1 frame |
| `Shift + ←` | Back 10 frames |
| `Shift + →` | Forward 10 frames |
| `← / →` | Seek backward/forward 5 seconds |

#### Workflow
1. Click **"📁 Load Video"** to select MP4 file
2. Play and position video at segment start
3. Press **S** to mark start (segment name field gets focus)
4. (Optional) Type custom segment name
5. Position video at segment end
6. Press **E** or **Enter** to save segment
7. Repeat for more segments
8. Click **"💾 Export Timestamps"** to save `timestamps.txt`

#### Output Format
```
Introduction;00:00:03.360;00:00:18.360
Main Content;00:00:27.360;00:00:42.360
Conclusion;00:01:15.120;00:01:45.890
```

---

### ⬇️ YouTube Downloader

**Usage:**
```bash
python3 firetimer-ytdownload.py -u <URL> -n <name> [OPTIONS]
```

FIRE - Video Processing Toolkit
=================================

FIRE provides four tools to record timestamps, download YouTube clips, cut videos into titled segments, and join parts.

Tools
-----
- `video_timestamp_recorder.py` — GUI for frame-accurate timestamps (exports `timestamps.txt`).
- `firetimer-ytdownload.py` — Download YouTube into `in-parts/` (defaults to `--name`) and auto-join.
- `firetimer-cutvid.py` — Cut local video by timestamps into `out-parts/`, adds title+timer overlays and auto-joins.
- `firetimer-joinvids.py` — Fast FFmpeg concat joiner (saves result one level above parts).

Install
-------
System requirements: Python 3.8+, FFmpeg on PATH, VLC (for the GUI).

Install Python dependencies:

```bash
pip install -r requirements.txt        # CLI (yt-dlp)
pip install -r requirements_gui.txt    # GUI (PyQt5, python-vlc) - optional
```

Quick usage
-----------
- Record timestamps (GUI):
	```bash
	python3 video_timestamp_recorder.py
	```
- Cut using timestamps:
	```bash
	python3 firetimer-cutvid.py -s video.mp4 -t timestamps.txt
	# output -> out-parts/ + final_out_video.mp4
	```
- Download (YouTube):
	```bash
	python3 firetimer-ytdownload.py -u <URL> -n <name>
	# output -> <name>/in-parts/ and joined final
	```
- Join parts manually:
	```bash
	python3 firetimer-joinvids.py -f path/to/parts -O final.mp4
	```

Important options (ytdownload)
------------------------------
- `--url, -u`  (required)
- `--name, -n` (required) — used as output filename and default folder name
- `--folder, -f` (optional)
- `--start, -s` / `--end, -e` — accept `SS`, `MM:SS`, `HH:MM:SS`
- `--chunk-minutes, -c` — how large each download chunk is (default 10 minutes)

Timestamp file format
---------------------
Each non-empty, non-comment line is a segment:

```
title;HH:MM:SS(.mmm);HH:MM:SS(.mmm)
```

Lines starting with `#` are ignored.

GUI recorder shortcuts
----------------------
- `S` = mark start
- `E` = mark end
- `N` = focus name input
- `Space` = play/pause
- `,` / `.` = frame −/+1
- `Shift` + arrow = frame ±10

Conventions and notes
---------------------
- `in-parts/` = downloaded input parts
- `out-parts/` = processed output parts
- Cutter re-encodes video to add overlays; joining copies streams when possible (fast).
- YT downloader pulls chunked segments and attempts to auto-join; chunk size defaults to 10 minutes.
- Segment titles are sanitized for file names (unsafe characters replaced).

Troubleshooting
---------------
- Install FFmpeg: `sudo apt install ffmpeg` (Linux) or `brew install ffmpeg` (macOS).
- Install VLC for GUI: `sudo apt install vlc` or `brew install vlc`.
- Make scripts executable if needed: `chmod +x *.py`.

Help and examples
-----------------
Run `--help` for any script to see full options and examples:

```bash
python3 firetimer-ytdownload.py --help
python3 firetimer-cutvid.py --help
python3 firetimer-joinvids.py --help
python3 video_timestamp_recorder.py  # launches GUI
```

License
-------
Open source — modify and redistribute.
```
