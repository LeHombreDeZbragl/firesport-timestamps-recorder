#!/usr/bin/env python3
"""
firetimer-cutvid.py - Cut video by timestamps with overlay title and timer

Usage:
  python3 firetimer-cutvid.py --source <video.mp4> --times <timestamps_file>

Required Arguments:
  --source, -s           Video source: local MP4 file path
  --times, -t            Timestamps file path

Timestamps File Format:
  Each non-empty, non-comment line should contain:
  title;start_time;end_time
  
  Example:
    Introduction;00:00:10;00:02:30
    Main Content;00:02:30;00:15:45
    Conclusion;00:15:45;00:18:20

Output:
  - Creates 'out-parts/' folder in same directory as source video
  - Each segment is saved with its title as filename
  - Overlays title and timer on each segment
  - Automatically joins all parts into final video

Examples:
  # Cut video using timestamps.txt
  python3 firetimer-cutvid.py -s myvideo.mp4 -t timestamps.txt
  
  # Cut video with custom timestamps file
  python3 firetimer-cutvid.py --source recording.mp4 --times segments.txt

Features:
  - Precise cutting with millisecond accuracy
  - Title overlay on each segment (bottom left)
  - Timer display starting from 00:00:00 (bottom right)
  - Automatic filename sanitization from titles
  - Auto-joins all segments into final video using firetimer-joinvids.py
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
    """Create out-parts directory in the same location as the video file."""
    video_dir = os.path.dirname(os.path.abspath(video_path))
    parts_dir = os.path.join(video_dir, "out-parts")
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

def sanitize_filename(title):
    """Convert title to safe filename by removing/replacing invalid characters."""
    # Replace invalid filename characters with underscores
    invalid_chars = '<>:"/\\|?*'
    filename = title
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Replace spaces with underscores and remove multiple underscores
    filename = filename.replace(' ', '_')
    filename = '_'.join(filter(None, filename.split('_')))  # Remove empty parts
    # Limit length and ensure it's not empty
    filename = filename[:50] if filename else "untitled"
    return filename

def timestamp_to_seconds(timestamp):
    """Convert HH:MM:SS.mmm to total seconds"""
    parts = timestamp.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds

def cut_and_label_segment(input_file, title, start, end, index, parts_dir):
    # Use title as filename instead of generic part{index}
    safe_filename = sanitize_filename(title)
    out = os.path.join(parts_dir, f"{safe_filename}.mp4")
    print(f"✂️  Cutting #{index + 1} '{title}' {start} → {end} → {out}")
    title_safe = ff_escape_text(title)
    
    # Calculate duration for proper cutting
    start_seconds = timestamp_to_seconds(start)
    end_seconds = timestamp_to_seconds(end)
    duration = end_seconds - start_seconds
    
    # Break down the timer expression into clear steps:
    # 1. Get seconds part (integer) - t will start from 0 due to setpts filter
    seconds_part = "eif\\:t\\:d"
    
    # 2. Get milliseconds (0-99 from t*100)
    milliseconds_raw = "mod(t*100\\,100)"
    
    # 3. Split milliseconds into tens and ones digits
    tens_digit = f"eif\\:{milliseconds_raw}/10\\:d"
    ones_digit = f"eif\\:mod({milliseconds_raw}\\,10)\\:d"
    
    # 4. Build complete timer string: "seconds.tensones"
    timer_text = f"%{{{seconds_part}}}.%{{{tens_digit}}}%{{{ones_digit}}}"
    
    # Reset video timestamps to 0 and apply overlays
    vf = (
        f"setpts=PTS-STARTPTS,"  # Force reset timestamps to start from 0
        f"drawtext=text='{title_safe}':fontcolor=white:fontsize=120:box=1:boxcolor=black@0.5:x=10:y=h-th-120,"
        f"drawtext=text='{timer_text}':fontcolor=white:fontsize=120:box=1:boxcolor=black@0.5:x=w-tw-10:y=h-th-120"
    )
    cmd = [
        "ffmpeg",
        "-ss", start, "-i", input_file,  # Seek before input for better timestamp reset
        "-t", str(duration),  # Use duration instead of end time
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast",  # Much faster encoding
        "-crf", "18",  # Better quality for faster preset
        "-c:a", "aac", "-b:a", "128k",  # Re-encode audio to avoid sync issues
        "-avoid_negative_ts", "make_zero",  # Handle timing issues
        "-fflags", "+genpts",  # Generate proper timestamps
        "-y", out
    ]
    subprocess.run(cmd, check=True)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Cut video by timestamps file with overlay title and timer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Timestamps File Format:
  Each line: title;start_time;end_time
  Example: Introduction;00:00:10;00:02:30

Output:
  - Creates 'out-parts/' folder in same directory as source video
  - Overlays title (bottom left) and timer (bottom right) on each segment
  - Auto-joins segments into final video

Examples:
  python3 firetimer-cutvid.py -s myvideo.mp4 -t timestamps.txt
  python3 firetimer-cutvid.py --source recording.mp4 --times segments.txt
        """
    )
    parser.add_argument("--source", "-s", required=True, help="Video source: local MP4 file path")
    parser.add_argument("--times", "-t", required=True, help="Timestamps file")
    args = parser.parse_args()

    check_deps()

    # Check if source file exists
    if not os.path.exists(args.source):
        print(f"ERROR: source file does not exist: {args.source}")
        sys.exit(1)

    # Create out-parts directory based on video location
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
    
    # Automatically call joinvids.py to join the cut parts
    print("\n🔗 Auto-joining cut parts...")
    try:
        joinvids_script = os.path.join(os.path.dirname(__file__), "firetimer-joinvids.py")
        if not os.path.exists(joinvids_script):
            print(f"⚠️  Warning: firetimer-joinvids.py not found at {joinvids_script}")
            print("   You can manually join the parts later.")
        else:
            # Run joinvids.py with the parts directory
            cmd = [sys.executable, joinvids_script, "--parts", parts_dir]
            print(f"🚀 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Auto-join completed successfully!")
            else:
                print(f"⚠️  Auto-join failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                print("   You can manually join the parts later.")
    except Exception as e:
        print(f"⚠️  Error during auto-join: {e}")
        print("   You can manually join the parts later.")

if __name__ == "__main__":
    main()
