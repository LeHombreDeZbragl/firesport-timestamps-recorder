# FIRE - Video Processing Toolkit

**FIRE** is a collection of Python scripts for video processing workflows: downloading from YouTube, cutting videos into segments with overlays, and joining multiple videos together.

---

## 🔥 Scripts Overview

### 1. `firetimer-ytdownload.py` - YouTube Video Downloader
Downloads videos from YouTube URLs to a specified folder with custom naming.

### 2. `firetimer-cutvid.py` - Video Segment Cutter
Cuts a video into segments based on timestamps, adding title and timer overlays to each segment.

### 3. `firetimer-joinvids.py` - Video Joiner
Joins multiple MP4 files into a single video with optional intro/outro clips.

---

## 📋 Requirements

- **Python 3.8+**
- **[FFmpeg](https://ffmpeg.org/)** (must be in your PATH)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** (Python package)

### Install Dependencies:
```bash
pip install yt-dlp
```

---

## 🚀 Usage

### 1. Download Video from YouTube

```bash
python3 firetimer-ytdownload.py --url <youtube_url> --folder <output_folder> --name <video_name>
```

**Parameters:**
- `--url, -u`: YouTube URL to download *(required)*
- `--folder, -f`: Output folder (created if doesn't exist) *(required)*  
- `--name, -n`: Video filename (without .mp4) *(required)*

**Example:**
```bash
python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n my_video
# Creates: downloads/my_video.mp4
```

### 2. Cut Video into Segments

```bash
python3 firetimer-cutvid.py --source <video.mp4> --times <timestamps_file>
```

**Parameters:**
- `--source, -s`: Local MP4 file path *(required)*
- `--times, -t`: Timestamps file *(required)*

**Example:**
```bash
python3 firetimer-cutvid.py -s video.mp4 -t timestamps.txt
# Creates: cut-vids/ folder with segmented videos
```

### 3. Join Videos Together

```bash
python3 firetimer-joinvids.py --folder <parts_folder> --out <output_name> [--intro intro.mp4] [--outro outro.mp4]
```

**Parameters:**
- `--folder, -f`: Folder containing MP4 parts *(required)*
- `--out, -O`: Output filename *(required)*
- `--intro, -i`: Optional intro video
- `--outro, -o`: Optional outro video

**Example:**
```bash
python3 firetimer-joinvids.py -f cut-vids -O final_video
# Creates: final_video.mp4 (one level above the parts folder)
```

---

## 📝 Timestamps File Format

For `firetimer-cutvid.py`, create a timestamps file with this format:

```
title;start_time;end_time
```

**Example `timestamps.txt`:**
```txt
# This is a comment
Intro;00:00:05;00:00:20
Main Scene;00:00:21;00:02:15
Conclusion;00:02:16;00:02:30
```

- **title**: Text overlaid on the segment (bottom-left)
- **start_time/end_time**: Timestamps in `HH:MM:SS` or `HH:MM:SS.sss` format
- Lines starting with `#` are ignored

---

## 📁 Output Structure

### After downloading:
```
folder/
└── video_name.mp4
```

### After cutting:
```
video_directory/
├── video.mp4
└── cut-vids/
    ├── part0.mp4
    ├── part1.mp4
    └── part2.mp4
```

### After joining:
```
parent_directory/
├── parts_folder/
│   ├── part0.mp4
│   └── part1.mp4
└── output_video.mp4  # Created here
```

---

## ⚡ Performance Notes

- **Video Cutting**: Uses re-encoding for overlays (slower but necessary for text)
- **Video Joining**: Uses stream copying (fast - seconds instead of minutes!)
- **Downloads**: Speed depends on your internet connection and YouTube servers

---

## 🛠️ Workflow Example

Complete workflow from YouTube to final video:

```bash
# 1. Download video
python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f project -n source_video

# 2. Cut into segments (creates project/cut-vids/)
python3 firetimer-cutvid.py -s project/source_video.mp4 -t timestamps.txt

# 3. Join segments (creates project/final_video.mp4)
python3 firetimer-joinvids.py -f project/cut-vids -O final_video
```

---

## 📄 License

This project is open source. Feel free to modify and distribute.