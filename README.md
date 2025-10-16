# FireTimer

**FireTimer** is a Python script to cut a video into segments based on a timestamps file, overlay each segment with a title and timer, and join all segments into a final video. It supports both local video files and YouTube URLs.

---

## Features

- Download videos from YouTube or use a local file.
- Cut video into multiple segments based on a timestamps file.
- Overlay each segment with:
  - Title (bottom-left)
  - Timer (bottom-right)
- Join all processed segments into one output video.
- Customizable output filename.

---

## Requirements

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/) (must be in your PATH)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Python package)

Install Python dependencies:

```bash
pip install yt-dlp
```
Usage
```bash
python3 firetimer.py --source <video_or_url> --times <timestamps_file> [--out output.mp4]
```
Arguments
```
--source, -s : Video source (local file path or YouTube URL)

--times, -t : Timestamps file

--out, -o : Output video filename (default: output.mp4)
```

Timestamps File Format
Each non-empty, non-comment line should have the following format:
```
title;start_time;end_time
```
title — text to overlay on the segment

start_time / end_time — timestamps in HH:MM:SS or HH:MM:SS.sss format

Lines starting with # are ignored

Example:

```txt
Intro;00:00:05;00:00:20
Main Scene;00:00:21;00:02:15
Outro;00:02:16;00:02:30
```

Segments are saved temporarily in _firetimer_helper/.

The final joined video is saved as specified by --out.

_firetimer_helper/ should be in .gitignore to avoid committing temporary files.

Notes
Ensure FFmpeg is installed and in your system PATH.

Supports overlaying longer titles and precise timestamps.