#!/usr/bin/env python3
"""
Usage:
  python3 firetimer-cutvids.py --source <video.mp4> --times <timestamps_file>

Timestamps file format (each non-empty non-comment line):
title;start_time;end_time

Creates a 'cut-vids' folder in the same directory as the source video.
"""
import argparse
import subprocess
import shutil
import sys
import os
import re

def check_deps():
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH. Install ffmpeg and ensure it's on PATH.")
        sys.exit(1)

def prepare_parts_dir(video_path):
    """Create cut-vids directory in the same location as the video file."""
    video_dir = os.path.dirname(os.path.abspath(video_path))
    parts_dir = os.path.join(video_dir, "cut-vids")
    if not os.path.exists(parts_dir):
        os.makedirs(parts_dir)
    return parts_dir

def fix_timestamp(ts):
    ts = ts.strip()
    if ts.count(':') >= 3:
        parts = ts.rsplit(':', 1)
        ts = parts[0] + '.' + parts[1]
    if not re.match(r'^\d{1,2}:\d{2}:\d{2}(\.\d+)?$', ts):
        raise ValueError(f"Invalid timestamp format: {ts}")
    h, m, s = ts.split(':')
    if '.' in s:
        s_int, s_frac = s.split('.', 1)
        s = f"{int(s_int):02d}.{s_frac}"
    else:
        s = f"{int(s):02d}"
    return f"{int(h):02d}:{int(m):02d}:{s}"

def parse_timestamps_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    segments = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = ln.split(";")
            if len(parts) < 3:
                print(f"Skipping invalid line: {ln}")
                continue
            title, start_raw, end_raw = parts[0].strip(), parts[1].strip(), parts[2].strip()
            try:
                start = fix_timestamp(start_raw)
                end = fix_timestamp(end_raw)
            except ValueError as e:
                print("Skipping line due to timestamp error:", e)
                continue
            segments.append((title, start, end))
    return segments

def ff_escape_text(s):
    s = s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
    return s

def cut_and_label_segment(input_file, title, start, end, index, parts_dir):
    out = os.path.join(parts_dir, f"part{index}.mp4")
    print(f"✂️  Cutting #{index + 1} '{title}' {start} → {end} → {out}")
    title_safe = ff_escape_text(title)
    pts_expr = "%{pts\\:hms}"
    # Bottom-left now, bigger fonts
    vf = (
        f"drawtext=text='{title_safe}':fontcolor=white:fontsize=56:box=1:boxcolor=black@0.5:x=10:y=h-th-60,"
        f"drawtext=text='{pts_expr}':fontcolor=white:fontsize=56:box=1:boxcolor=black@0.5:x=w-tw-10:y=h-th-60"
    )
    cmd = [
        "ffmpeg",
        "-ss", start, "-to", end, "-i", input_file,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-y", out
    ]
    subprocess.run(cmd, check=True)
    return out


def main():
    parser = argparse.ArgumentParser(description="Cut video by timestamps file, overlay title+timer.")
    parser.add_argument("--source", "-s", required=True, help="Video source: local MP4 file path")
    parser.add_argument("--times", "-t", required=True, help="Timestamps file")
    args = parser.parse_args()

    check_deps()

    # Check if source file exists
    if not os.path.exists(args.source):
        print(f"ERROR: source file does not exist: {args.source}")
        sys.exit(1)

    # Create cut-vids directory based on video location
    parts_dir = prepare_parts_dir(args.source)
    print(f"📁 Cut videos will be saved to: {parts_dir}")

    segments = parse_timestamps_file(args.times)
    if not segments:
        print("No valid segments found. Exiting.")
        sys.exit(1)

    parts = []
    for i, (title, start, end) in enumerate(segments):
        part = cut_and_label_segment(args.source, title, start, end, i, parts_dir)
        parts.append(part)

    # Remove parts.txt file if it exists
    parts_txt_path = os.path.join(parts_dir, "parts.txt")
    if os.path.exists(parts_txt_path):
        os.remove(parts_txt_path)
        print(f"🗑️  Removed {parts_txt_path}")

    print(f"✅ All {len(parts)} cut videos have been saved to: {parts_dir}")

if __name__ == "__main__":
    main()
