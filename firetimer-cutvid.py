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
            # New format: title;začátek;start;koš;voda;kohout;rozdělovač;výstřik;LP;PP;konec
            # Old format: title;start;end
            if len(parts) >= 11:
                # New format with splits
                title = parts[0].strip()
                zacatek = parts[1].strip()  # začátek (not used for timer)
                split_start = parts[2].strip()  # start (timer reference)
                split_kos = parts[3].strip()
                split_voda = parts[4].strip()
                split_kohout = parts[5].strip()
                split_rozdelovac = parts[6].strip()
                split_vystrik = parts[7].strip()
                split_lp = parts[8].strip()
                split_pp = parts[9].strip()
                konec = parts[10].strip()
                
                try:
                    start = fix_timestamp(zacatek)
                    end = fix_timestamp(konec)
                    
                    # Parse splits - they are already in relative seconds format (00.000)
                    # Just store them as-is for now, we'll use them later
                    splits = {
                        'start': split_start,
                        'koš': split_kos,
                        'voda': split_voda,
                        'kohout': split_kohout,
                        'rozdělovač': split_rozdelovac,
                        'výstřik': split_vystrik,
                        'LP': split_lp,
                        'PP': split_pp
                    }
                    
                    segments.append((title, start, end, splits))
                except ValueError as e:
                    print("Skipping line due to timestamp error:", e)
                    continue
            elif len(parts) >= 3:
                # Old format without splits
                title, start_raw, end_raw = parts[0].strip(), parts[1].strip(), parts[2].strip()
                try:
                    start = fix_timestamp(start_raw)
                    end = fix_timestamp(end_raw)
                    segments.append((title, start, end, {}))
                except ValueError as e:
                    print("Skipping line due to timestamp error:", e)
                    continue
            else:
                print(f"Skipping invalid line: {ln}")
                continue
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

def cut_and_label_segment(input_file, title, start, end, index, parts_dir, splits=None):
    # Use title as filename instead of generic part{index}
    safe_filename = sanitize_filename(title)
    out = os.path.join(parts_dir, f"{safe_filename}.mp4")
    print(f"✂️  Cutting #{index + 1} '{title}' {start} → {end} → {out}")
    title_safe = ff_escape_text(title)
    
    # Calculate duration for proper cutting
    start_seconds = timestamp_to_seconds(start)  # začátek timestamp
    end_seconds = timestamp_to_seconds(end)      # konec timestamp
    duration = end_seconds - start_seconds
    
    # Calculate timer offset and stop time from splits
    timer_offset = 0.0
    timer_stop_time = duration  # Default: stop at end
    
    if splits and 'start' in splits:
        start_split_timestamp = splits['start'].strip()
        # Convert start split absolute timestamp to seconds
        try:
            start_split_seconds = timestamp_to_seconds(start_split_timestamp)
            # Calculate offset: how many seconds after začátek is the "start" split
            timer_offset = start_split_seconds - start_seconds
            
            # Find the maximum of LP and PP to determine when timer stops
            lp_seconds = 0
            pp_seconds = 0
            
            if 'LP' in splits and splits['LP'].strip():
                try:
                    lp_seconds = timestamp_to_seconds(splits['LP'].strip())
                except:
                    pass
            
            if 'PP' in splits and splits['PP'].strip():
                try:
                    pp_seconds = timestamp_to_seconds(splits['PP'].strip())
                except:
                    pass
            
            # Timer stops at the maximum of LP and PP (relative to začátek)
            if lp_seconds > 0 or pp_seconds > 0:
                max_split_seconds = max(lp_seconds, pp_seconds)
                timer_stop_time = max_split_seconds - start_seconds
        except:
            timer_offset = 0.0
    
    # Calculate the final timer value (when it stops)
    final_timer_value = timer_stop_time - timer_offset
    
    # Build timer text with conditions:
    # - Before start (t < timer_offset): show 00.00
    # - From start to stop (timer_offset <= t < timer_stop_time): show increasing time
    # - After stop (t >= timer_stop_time): show final value (frozen)
    
    # Current time relative to start
    time_from_start = f"t-{timer_offset}"
    
    # Conditional timer value:
    # if t < timer_offset: 0
    # elif t >= timer_stop_time: final_value
    # else: t - timer_offset
    timer_value = f"if(lt(t\\,{timer_offset})\\,0\\,if(gte(t\\,{timer_stop_time})\\,{final_timer_value}\\,{time_from_start}))"
    
    seconds_part = f"eif\\:{timer_value}\\:d"
    # For centiseconds (2 decimal places): 0-99
    centiseconds_raw = f"mod({timer_value}*100\\,100)"
    tens_digit = f"eif\\:{centiseconds_raw}/10\\:d"
    ones_digit = f"eif\\:mod({centiseconds_raw}\\,10)\\:d"
    timer_text = f"%{{{seconds_part}}}.%{{{tens_digit}}}%{{{ones_digit}}}"
    
    # Build drawtext filters
    filters = ["setpts=PTS-STARTPTS"]  # Reset timestamps to start from 0
    
    # Title overlay (bottom left, smaller font, at the very bottom)
    filters.append(
        f"drawtext=text='{title_safe}':fontcolor=white:fontsize=80:box=1:boxcolor=black@0.5:x=10:y=h-th-10"
    )
    
    # Timer overlay (bottom right, smaller font, at the very bottom)
    filters.append(
        f"drawtext=text='{timer_text}':fontcolor=white:fontsize=80:box=1:boxcolor=black@0.5:x=w-tw-10:y=h-th-10"
    )
    
    # Add split overlays above the timer (if splits are provided)
    if splits:
        split_names = ['koš', 'voda', 'kohout', 'rozdělovač', 'výstřik', 'LP', 'PP']
        y_offset = 100  # Start position above timer (adjusted for smaller font)
        
        # Get start split timestamp for calculating relative times
        start_split_timestamp = splits.get('start', '').strip()
        if start_split_timestamp:
            try:
                start_split_seconds = timestamp_to_seconds(start_split_timestamp)
                
                for split_name in split_names:
                    if split_name in splits:
                        split_timestamp = splits[split_name].strip()
                        # Check if it's a valid non-zero timestamp
                        if split_timestamp and split_timestamp != "00:00:00.000":
                            try:
                                # Convert absolute timestamp to seconds
                                split_seconds = timestamp_to_seconds(split_timestamp)
                                # Calculate relative to "start" split
                                relative_seconds = split_seconds - start_split_seconds
                                
                                # Calculate when this split should appear (relative to začátek)
                                split_appears_at = split_seconds - start_seconds
                                
                                # Format with 2 decimal places
                                split_formatted = f"{relative_seconds:.2f}"
                                
                                # Format: "koš: 3.50" or "voda: 12.25"
                                split_text = f"{split_name}: {split_formatted}"
                                split_text_safe = ff_escape_text(split_text)
                                
                                # Add split overlay with enable condition (appears only after its time)
                                # enable='gte(t,split_appears_at)'
                                filters.append(
                                    f"drawtext=text='{split_text_safe}':fontcolor=white:fontsize=60:box=1:boxcolor=black@0.5:x=w-tw-10:y=h-{y_offset}:enable='gte(t\\,{split_appears_at})'"
                                )
                                y_offset += 70  # Move up for next split
                            except:
                                continue
            except:
                pass
    
    # Join all filters
    vf = ",".join(filters)
    
    cmd = [
        "ffmpeg",
        "-ss", start, "-i", input_file,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        "-fflags", "+genpts",
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
    for i, seg_data in enumerate(segments):
        # Unpack based on tuple length (old format: 3, new format: 4)
        if len(seg_data) == 3:
            title, start, end = seg_data
            splits = None
        else:
            title, start, end, splits = seg_data
        
        part = cut_and_label_segment(args.source, title, start, end, i, parts_dir, splits)
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
