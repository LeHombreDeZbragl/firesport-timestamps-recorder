#!/usr/bin/env python3
"""
add-timer.py - Add a running timer overlay to a video

Usage:
  python3 add-timer.py --source <video.mp4> [options]

Required Arguments:
  --source, -s           Input video file path

Optional Arguments:
  --start                Absolute timestamp when timer starts counting (HH:MM:SS.mmm)
                         Default: beginning of video (00:00:00.000)
  --end                  Absolute timestamp when timer freezes (HH:MM:SS.mmm)
                         Default: end of video
  --end-relative         Duration from --start when timer freezes (HH:MM:SS.mmm)
                         Mutually exclusive with --end
  --output, -o           Output file path
                         Default: <source_stem>_timer.mp4 in same directory

Timer Behavior:
  Before --start     : timer shows 00.00 (frozen at zero)
  Between start/end  : timer counts up
  After --end        : timer frozen at final value

Examples:
  # Add timer to whole video
  python3 add-timer.py -s myvideo.mp4

  # Timer starts at 5s and freezes at 20s
  python3 add-timer.py -s myvideo.mp4 --start 00:00:05.000 --end 00:00:20.000

  # Timer starts at 5s and runs for 15 seconds (end-relative)
  python3 add-timer.py -s myvideo.mp4 --start 00:00:05.000 --end-relative 00:00:15.000

  # Custom output path
  python3 add-timer.py -s myvideo.mp4 --start 00:00:03.000 -o result.mp4
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


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"ERROR: Could not determine video duration: {e}")
        sys.exit(1)


def timestamp_to_seconds(timestamp):
    """Convert HH:MM:SS.mmm to total seconds."""
    parts = timestamp.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def build_timer_filters(duration, timer_offset, timer_stop_time):
    """Build ffmpeg drawtext filter chain for timer overlay (always visible, no animation)."""
    final_timer_value = timer_stop_time - timer_offset

    # Timer value expression:
    #   t < timer_offset            -> 0 (frozen at start)
    #   timer_offset <= t < stop    -> t - timer_offset (counting)
    #   t >= timer_stop_time        -> final_timer_value (frozen at end)
    time_from_start = f"t-{timer_offset}"
    timer_value = (
        f"if(lt(t\\,{timer_offset})\\,0"
        f"\\,if(gte(t\\,{timer_stop_time})\\,{final_timer_value}"
        f"\\,{time_from_start}))"
    )

    # Digit decomposition for fixed-width display (prevents width jumping)
    seconds_tens      = f"eif\\:{timer_value}/10\\:d"
    seconds_ones      = f"eif\\:mod({timer_value}\\,10)\\:d"
    centiseconds_raw  = f"mod({timer_value}*100\\,100)"
    centiseconds_tens = f"eif\\:{centiseconds_raw}/10\\:d"
    centiseconds_ones = f"eif\\:mod({centiseconds_raw}\\,10)\\:d"

    timer_seconds_tens = f"%{{{seconds_tens}}}"
    timer_seconds_ones = f"%{{{seconds_ones}}}"
    timer_colon        = "\\:"
    timer_centis_tens  = f"%{{{centiseconds_tens}}}"
    timer_centis_ones  = f"%{{{centiseconds_ones}}}"

    # Only show tens digit when value >= 10 seconds
    show_seconds_tens = f"gte({timer_value}\\,10)"

    filters = ["setpts=PTS-STARTPTS"]

    # Smooth gradient bar at the bottom (same as firetimer-cutvid.py)
    bar_height = 140
    step = 3
    for i in range(0, bar_height, step):
        progress = i / bar_height
        opacity = 0.15 + (0.9 - 0.15) * progress
        y_pos = f"ih-{bar_height - i}"
        filters.append(f"drawbox=x=0:y={y_pos}:w=iw:h={step}:color=0x828082@{opacity:.3f}:t=fill")

    # Timer digits (bottom right, always visible)
    timer_fontsize = 80
    timer_y = "h-th-40"
    base_x = 190  # rightmost digit offset from right edge

    # Build from right to left: ones-of-centis, tens-of-centis, colon, ones-of-seconds, tens-of-seconds
    filters.append(
        f"drawtext=text='{timer_centis_ones}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x}:y={timer_y}"
    )
    filters.append(
        f"drawtext=text='{timer_centis_tens}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 50}:y={timer_y}"
    )
    filters.append(
        f"drawtext=text='{timer_colon}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 76}:y={timer_y}"
    )
    filters.append(
        f"drawtext=text='{timer_seconds_ones}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 124}:y={timer_y}"
    )
    filters.append(
        f"drawtext=text='{timer_seconds_tens}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 174}:y={timer_y}:enable='{show_seconds_tens}'"
    )

    return filters


def main():
    parser = argparse.ArgumentParser(
        description="Add a running timer overlay to a video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Timer Behavior:
  Before --start     : timer shows 00.00 (frozen at zero)
  Between start/end  : timer counts up
  After --end        : timer frozen at final value

All timestamps use HH:MM:SS.mmm format (e.g. 00:00:05.000).

Examples:
  # Add timer to whole video
  python3 add-timer.py -s myvideo.mp4

  # Timer starts at 5s and freezes at 20s
  python3 add-timer.py -s myvideo.mp4 --start 00:00:05.000 --end 00:00:20.000

  # Timer starts at 5s and runs for 15 seconds (relative end)
  python3 add-timer.py -s myvideo.mp4 --start 00:00:05.000 --end-relative 00:00:15.000

  # Custom output path
  python3 add-timer.py -s myvideo.mp4 --start 00:00:03.000 -o result.mp4
        """
    )
    parser.add_argument("--source", "-s", required=True,
                        help="Input video file path")
    parser.add_argument("--start", default=None, metavar="HH:MM:SS.mmm",
                        help="Absolute timestamp when timer starts counting (default: beginning of video)")

    end_group = parser.add_mutually_exclusive_group()
    end_group.add_argument("--end", default=None, metavar="HH:MM:SS.mmm",
                           help="Absolute timestamp when timer freezes (default: end of video)")
    end_group.add_argument("--end-relative", default=None, dest="end_relative", metavar="HH:MM:SS.mmm",
                           help="Duration from --start when timer freezes (alternative to --end)")

    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (default: <source_stem>_timer.mp4)")
    args = parser.parse_args()

    check_deps()

    if not os.path.exists(args.source):
        print(f"ERROR: source file does not exist: {args.source}")
        sys.exit(1)

    duration = get_video_duration(args.source)
    print(f"📹 Video duration: {duration:.3f}s")

    # Resolve timer_offset
    if args.start:
        try:
            timer_offset = timestamp_to_seconds(fix_timestamp(args.start))
        except ValueError as e:
            print(f"ERROR: invalid --start timestamp: {e}")
            sys.exit(1)
    else:
        timer_offset = 0.0

    # Resolve timer_stop_time
    if args.end:
        try:
            timer_stop_time = timestamp_to_seconds(fix_timestamp(args.end))
        except ValueError as e:
            print(f"ERROR: invalid --end timestamp: {e}")
            sys.exit(1)
    elif args.end_relative:
        try:
            relative_seconds = timestamp_to_seconds(fix_timestamp(args.end_relative))
            timer_stop_time = timer_offset + relative_seconds
        except ValueError as e:
            print(f"ERROR: invalid --end-relative timestamp: {e}")
            sys.exit(1)
    else:
        timer_stop_time = duration

    # Clamp to valid range
    timer_offset    = max(0.0, min(timer_offset,    duration))
    timer_stop_time = max(timer_offset, min(timer_stop_time, duration))

    # Resolve output path
    if args.output:
        out_path = args.output
    else:
        base, ext = os.path.splitext(args.source)
        out_path = f"{base}_timer{ext if ext else '.mp4'}"

    print(f"⏱️  Timer: starts counting at {timer_offset:.3f}s, freezes at {timer_stop_time:.3f}s")
    print(f"💾 Output: {out_path}")

    filters = build_timer_filters(duration, timer_offset, timer_stop_time)
    vf = ",".join(filters)

    cmd = [
        "ffmpeg",
        "-i", args.source,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-y", out_path
    ]

    print("🔧 Running ffmpeg...")
    subprocess.run(cmd, check=True)
    print(f"✅ Done: {out_path}")


if __name__ == "__main__":
    main()
