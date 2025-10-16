#!/usr/bin/env python3
"""
Usage:
  python3 firetimer.py --source <video_or_url> --times <timestamps_file> [--out output.mp4]

Timestamps file format (each non-empty non-comment line):
title;start_time;end_time
"""
import argparse
import subprocess
import shutil
import sys
import os
import re
import yt_dlp

HELPER_DIR = "_firetimer_helper"

def check_deps():
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH. Install ffmpeg and ensure it's on PATH.")
        sys.exit(1)

def prepare_helper_dir():
    if not os.path.exists(HELPER_DIR):
        os.makedirs(HELPER_DIR)

def download_video(url, filename=None):
    if filename is None:
        filename = os.path.join(HELPER_DIR, "input.mp4")
    print(f"⬇️  Downloading video from {url} → {filename}")
    ydl_opts = {
        "outtmpl": filename,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    print("✅ Download complete.")
    return filename

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

def cut_and_label_segment(input_file, title, start, end, index):
    out = os.path.join(HELPER_DIR, f"part{index}.mp4")
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

def join_parts(parts, output_file="output.mp4"):
    print("🔗 Joining parts...")
    parts_list_file = os.path.join(HELPER_DIR, "parts.txt")
    with open(parts_list_file, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")  # <-- use absolute paths here
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", parts_list_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-y", os.path.abspath(output_file)  # <-- optional: absolute output path
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Final video: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Cut video by timestamps file, overlay title+timer, join parts.")
    parser.add_argument("--source", "-s", required=True, help="Video source: local file path or YouTube URL")
    parser.add_argument("--times", "-t", required=True, help="Timestamps file")
    parser.add_argument("--out", "-o", default="output.mp4", help="Output filename")
    args = parser.parse_args()

    check_deps()
    prepare_helper_dir()

    # Determine input file
    src = args.source
    input_file = os.path.join(HELPER_DIR, "input.mp4")
    if re.match(r'^https?://', src):
        input_file = download_video(src, filename=input_file)
    else:
        if not os.path.exists(src):
            print("ERROR: source file does not exist:", src)
            sys.exit(1)
        input_file = src

    segments = parse_timestamps_file(args.times)
    if not segments:
        print("No valid segments found. Exiting.")
        sys.exit(1)

    parts = []
    for i, (title, start, end) in enumerate(segments):
        part = cut_and_label_segment(input_file, title, start, end, i)
        parts.append(part)

    join_parts(parts, args.out)

if __name__ == "__main__":
    main()
