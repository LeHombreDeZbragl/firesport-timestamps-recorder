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
  title;začátek;start;koš;voda;kohout;rozdělovač;výstřik_LP;výstřik_PP;LP;PP;konec
  
  Example:
    Zbraslav;00:00:11.900;00:00:16.901;00:00:17.400;00:00:18.151;00:00:18.402;00:00:19.151;00:00:19.651;00:00:19.901;00:00:20.400;00:00:20.901;00:00:21.901

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

def validate_timestamps_file(path):
    """Validate timestamps file and return list of warnings.
    Returns (is_valid, warnings_list)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    
    warnings = []
    line_number = 0
    
    def is_empty_or_zero(ts):
        """Check if timestamp is empty or zero (00:00:00.000)"""
        return not ts or ts == "00:00:00.000"
    
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            line_number += 1
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            
            parts = ln.split(";")
            
            # Check if line has exactly 12 parts
            if len(parts) != 12:
                warnings.append(f"Line {line_number}: Expected exactly 12 parts, found {len(parts)}")
                continue
            
            # Extract parts
            title = parts[0].strip()
            zacatek = parts[1].strip()
            split_start = parts[2].strip()
            split_kos = parts[3].strip()
            split_voda = parts[4].strip()
            split_kohout = parts[5].strip()
            split_rozdelovac = parts[6].strip()
            split_vystrik_lp = parts[7].strip()
            split_vystrik_pp = parts[8].strip()
            split_lp = parts[9].strip()
            split_pp = parts[10].strip()
            konec = parts[11].strip()
            
            title_info = f" (title: {title})" if title else ""
            
            # Check if title (parts[0]) is empty
            if not title:
                warnings.append(f"Line {line_number}: is missing a title")
            
            # Check if required timestamps are empty or zero
            if is_empty_or_zero(zacatek):
                warnings.append(f"Line {line_number}: začátek is missing or zero{title_info}")
            
            if is_empty_or_zero(split_start):
                warnings.append(f"Line {line_number}: start is missing or zero{title_info}")
            
            if is_empty_or_zero(konec):
                warnings.append(f"Line {line_number}: konec is missing or zero{title_info}")
            
            # Validate timestamp ordering (only if all required timestamps are present)
            if not is_empty_or_zero(zacatek) and not is_empty_or_zero(split_start) and not is_empty_or_zero(konec):
                try:
                    # Convert timestamps to seconds for comparison
                    ts_zacatek = timestamp_to_seconds(zacatek)
                    ts_start = timestamp_to_seconds(split_start)
                    ts_kos = timestamp_to_seconds(split_kos) if not is_empty_or_zero(split_kos) else None
                    ts_voda = timestamp_to_seconds(split_voda) if not is_empty_or_zero(split_voda) else None
                    ts_kohout = timestamp_to_seconds(split_kohout) if not is_empty_or_zero(split_kohout) else None
                    ts_rozdelovac = timestamp_to_seconds(split_rozdelovac) if not is_empty_or_zero(split_rozdelovac) else None
                    ts_vystrik_lp = timestamp_to_seconds(split_vystrik_lp) if not is_empty_or_zero(split_vystrik_lp) else None
                    ts_vystrik_pp = timestamp_to_seconds(split_vystrik_pp) if not is_empty_or_zero(split_vystrik_pp) else None
                    ts_lp = timestamp_to_seconds(split_lp) if not is_empty_or_zero(split_lp) else None
                    ts_pp = timestamp_to_seconds(split_pp) if not is_empty_or_zero(split_pp) else None
                    ts_konec = timestamp_to_seconds(konec)
                    
                    # Rule 1: začátek must be the lowest
                    if ts_start <= ts_zacatek:
                        warnings.append(f"Line {line_number}: start must be greater than začátek{title_info}")
                    
                    # Rule 2: start < koš (if koš exists)
                    if ts_kos is not None and ts_kos <= ts_start:
                        warnings.append(f"Line {line_number}: koš must be greater than start{title_info}")
                    
                    # Rule 3: koš < voda (if both exist)
                    if ts_kos is not None and ts_voda is not None and ts_voda <= ts_kos:
                        warnings.append(f"Line {line_number}: voda must be greater than koš{title_info}")
                    
                    # Rule 4: voda < kohout (if both exist)
                    if ts_voda is not None and ts_kohout is not None and ts_kohout <= ts_voda:
                        warnings.append(f"Line {line_number}: kohout must be greater than voda{title_info}")
                    
                    # Rule 5: kohout < rozdělovač (if both exist)
                    if ts_kohout is not None and ts_rozdelovac is not None and ts_rozdelovac <= ts_kohout:
                        warnings.append(f"Line {line_number}: rozdělovač must be greater than kohout{title_info}")
                    
                    # Rule 6: rozdělovač < výstřik_LP (if both exist)
                    if ts_rozdelovac is not None and ts_vystrik_lp is not None and ts_vystrik_lp <= ts_rozdelovac:
                        warnings.append(f"Line {line_number}: výstřik_LP must be greater than rozdělovač{title_info}")
                    
                    # Rule 7: rozdělovač < výstřik_PP (if both exist)
                    if ts_rozdelovac is not None and ts_vystrik_pp is not None and ts_vystrik_pp <= ts_rozdelovac:
                        warnings.append(f"Line {line_number}: výstřik_PP must be greater than rozdělovač{title_info}")
                    
                    # Rule 8: výstřik_LP < LP (if both exist)
                    if ts_vystrik_lp is not None and ts_lp is not None and ts_lp <= ts_vystrik_lp:
                        warnings.append(f"Line {line_number}: LP must be greater than výstřik_LP{title_info}")
                    
                    # Rule 9: výstřik_PP < PP (if both exist)
                    if ts_vystrik_pp is not None and ts_pp is not None and ts_pp <= ts_vystrik_pp:
                        warnings.append(f"Line {line_number}: PP must be greater than výstřik_PP{title_info}")
                    
                    # Rule 10: konec must be the biggest
                    all_timestamps = [ts for ts in [ts_zacatek, ts_start, ts_kos, ts_voda, ts_kohout, 
                                                     ts_rozdelovac, ts_vystrik_lp, ts_vystrik_pp, 
                                                     ts_lp, ts_pp] if ts is not None]
                    if all_timestamps and ts_konec <= max(all_timestamps):
                        warnings.append(f"Line {line_number}: konec must be greater than all other timestamps{title_info}")
                    
                except Exception as e:
                    warnings.append(f"Line {line_number}: Error validating timestamp order: {e}{title_info}")
    
    is_valid = len(warnings) == 0
    return is_valid, warnings

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
            
            # New format: title;začátek;start;koš;voda;kohout;rozdělovač;výstřik_LP;výstřik_PP;LP;PP;konec
            if len(parts) == 12:
                # New format with splits
                title = parts[0].strip()
                zacatek = parts[1].strip()  # začátek (not used for timer)
                split_start = parts[2].strip()  # start (timer reference)
                split_kos = parts[3].strip()
                split_voda = parts[4].strip()
                split_kohout = parts[5].strip()
                split_rozdelovac = parts[6].strip()
                split_vystrik_lp = parts[7].strip()
                split_vystrik_pp = parts[8].strip()
                split_lp = parts[9].strip()
                split_pp = parts[10].strip()
                konec = parts[11].strip()
                
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
                        'výstřik_LP': split_vystrik_lp,
                        'výstřik_PP': split_vystrik_pp,
                        'LP': split_lp,
                        'PP': split_pp
                    }
                    
                    segments.append((title, start, end, splits))
                except ValueError as e:
                    print("Skipping line due to timestamp error:", e)
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

def cut_and_label_segment(input_file, title, start, end, index, parts_dir, splits=None, label=None, order_prefix=None):
    # Use title as filename instead of generic part{index}
    safe_filename = sanitize_filename(title)
    
    # Add ordering prefix to filename if provided
    if order_prefix is not None:
        filename = f"{order_prefix:03d}_{safe_filename}.mp4"
    else:
        filename = f"{safe_filename}.mp4"
    
    out = os.path.join(parts_dir, filename)
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
            # If both are missing, timer doesn't stop (runs until end)
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
    
    # Split timer into individual digit components for fixed-width display
    seconds_total = f"eif\\:{timer_value}\\:d"
    seconds_tens = f"eif\\:{timer_value}/10\\:d"
    seconds_ones = f"eif\\:mod({timer_value}\\,10)\\:d"
    centiseconds_raw = f"mod({timer_value}*100\\,100)"
    centiseconds_tens = f"eif\\:{centiseconds_raw}/10\\:d"
    centiseconds_ones = f"eif\\:mod({centiseconds_raw}\\,10)\\:d"
    
    # Individual text elements for each part
    timer_seconds_tens = f"%{{{seconds_tens}}}"
    timer_seconds_ones = f"%{{{seconds_ones}}}"
    timer_colon = "\\:"
    timer_centis_tens = f"%{{{centiseconds_tens}}}"
    timer_centis_ones = f"%{{{centiseconds_ones}}}"
    
    # Condition for showing tens digit (only when >= 10)
    show_seconds_tens = f"gte({timer_value}\\,10)"
    
    # Calculate when koš appears (for title slide-out animation)
    # Title should start sliding out 1 second BEFORE koš appears
    kos_appears_at = None
    if splits:
        start_split_timestamp = splits.get('start', '').strip()
        if start_split_timestamp:
            try:
                start_split_seconds = timestamp_to_seconds(start_split_timestamp)
                if 'koš' in splits and splits['koš'].strip() and splits['koš'].strip() != "00:00:00.000":
                    kos_seconds = timestamp_to_seconds(splits['koš'].strip())
                    # Start sliding 1 second BEFORE koš appears
                    kos_appears_at = (kos_seconds - start_seconds) - 1.0
                else:
                    # If koš doesn't exist, use timer_offset + 3 seconds
                    kos_appears_at = timer_offset + 3.0
            except:
                pass
    
    # If kos_appears_at is still None, set it to 3 seconds after timer starts
    if kos_appears_at is None:
        kos_appears_at = timer_offset + 3.0
    
    # Build drawtext filters
    filters = ["setpts=PTS-STARTPTS"]  # Reset timestamps to start from 0
    
    # Add full-width grey bar at the bottom with smooth gradient transparency
    # Create smooth gradient by stacking boxes every 3 pixels with gradually increasing opacity
    bar_height = 140
    step = 3  # Height of each box layer in pixels
    
    for i in range(0, bar_height, step):
        # Calculate opacity: starts at 0.7 at top, goes to 1 at bottom
        # Linear interpolation: opacity = min_opacity + (max_opacity - min_opacity) * progress
        progress = i / bar_height  # 0.0 at top, 1.0 at bottom
        opacity = 0.7 + (1.0 - 0.7) * progress
        
        # Y position: starts from top of bar (ih-140) and goes down
        y_pos = f"ih-{bar_height - i}"
        
        filters.append(f"drawbox=x=0:y={y_pos}:w=iw:h={step}:color=0x848484@{opacity:.3f}:t=fill")
    
    # Title overlay (bottom left, smaller font, at the very bottom)
    # Label is now to the right of the title on the same line
    # Animate: slide down out of view when koš appears
    # Title overlay (bottom left, smaller font, at the very bottom)
    # Label is now to the right of the title on the same line
    # Animate: slide in from bottom at start, slide down out of view when koš appears
    title_slide_in_start = 0.2  # Start sliding in at 0.2 seconds
    title_slide_in_duration = 1.0  # Take 1 second to slide in
    title_slide_in_end = title_slide_in_start + title_slide_in_duration
    
    if label is not None:
        label_safe = ff_escape_text(label)
        # Combined title and label on same line
        # Format based on label type:
        # - For "X.místo": "X. title" or "NP title" if label is "NP"
        # - For "X.útok": "X.útok title" (even if NP, though that shouldn't happen)
        if label == "NP":
            combined_text = f"NP {title_safe}"
        elif ".místo" in label:
            # Extract the number and format as "X. title"
            position_num = label.replace(".místo", "")
            combined_text = f"{position_num}. {title_safe}"
        elif ".útok" in label:
            # Format as "X.útok title"
            combined_text = f"{label_safe} {title_safe}"
        else:
            # Fallback to old format
            combined_text = f"{title_safe} - {label_safe}"
        
        # Y position animation: slide in at start, then slide out when koš appears (or 4s after timer start)
        title_slide_out_duration = 0.8
        title_slide_out_start = kos_appears_at
        title_slide_out_end = kos_appears_at + title_slide_out_duration
        # Before slide-in: off-screen (h+100)
        # During slide-in: h+100 to h-th-30
        # After slide-in, before slide-out: h-th-30
        # During slide-out: h-th-30 to h+100
        # After slide-out: h+100
        title_y = f"if(lt(t\\,{title_slide_in_start})\\,h+100\\,if(lt(t\\,{title_slide_in_end})\\,h+100-((t-{title_slide_in_start})/{title_slide_in_duration})*(130+th)\\,if(lt(t\\,{title_slide_out_start})\\,h-th-30\\,if(gte(t\\,{title_slide_out_end})\\,h+100\\,h-th-30+((t-{title_slide_out_start})/{title_slide_out_duration})*(130+th)))))"
        
        filters.append(
            f"drawtext=text='{combined_text}':fontcolor=white:fontsize=60:x=45:y={title_y}"
        )
    else:
        # Y position animation: slide in at start, then slide out when koš appears (or 4s after timer start)
        title_slide_out_duration = 0.8
        title_slide_out_start = kos_appears_at
        title_slide_out_end = kos_appears_at + title_slide_out_duration
        # Before slide-in: off-screen (h+100)
        # During slide-in: h+100 to h-th-30
        # After slide-in, before slide-out: h-th-30
        # During slide-out: h-th-30 to h+100
        # After slide-out: h+100
        title_y = f"if(lt(t\\,{title_slide_in_start})\\,h+100\\,if(lt(t\\,{title_slide_in_end})\\,h+100-((t-{title_slide_in_start})/{title_slide_in_duration})*(130+th)\\,if(lt(t\\,{title_slide_out_start})\\,h-th-30\\,if(gte(t\\,{title_slide_out_end})\\,h+100\\,h-th-30+((t-{title_slide_out_start})/{title_slide_out_duration})*(130+th)))))"
        
        filters.append(
            f"drawtext=text='{title_safe}':fontcolor=white:fontsize=60:x=45:y={title_y}"
        )
    
    # Timer overlay (bottom right) - separate elements to prevent width glitching
    # Base position for rightmost edge
    # Animate: slide in at start (same timing as title), slide down 1 second before end of video
    timer_fontsize = 80
    timer_slide_in_start = 0.2  # Same as title
    timer_slide_in_duration = 1.0  # Same as title
    timer_slide_in_end = timer_slide_in_start + timer_slide_in_duration
    timer_slide_out_start = duration - 1.0  # Start sliding out 1 second before end
    timer_slide_out_duration = 1.0
    timer_slide_out_end = timer_slide_out_start + timer_slide_out_duration
    # Timer Y animation: slide in from bottom, stay visible, then slide down at end
    # Before slide-in: h+100, During slide-in: animate to h-th-40, Stay visible, Then slide out to h+100
    timer_y = f"if(lt(t\\,{timer_slide_in_start})\\,h+100\\,if(lt(t\\,{timer_slide_in_end})\\,h+100-((t-{timer_slide_in_start})/{timer_slide_in_duration})*(140+th)\\,if(lt(t\\,{timer_slide_out_start})\\,h-th-40\\,if(gte(t\\,{timer_slide_out_end})\\,h+100\\,h-th-40+((t-{timer_slide_out_start})/{timer_slide_out_duration})*(140+th)))))"
    
    # Position elements from right to left with fixed positions to prevent jumping
    # Using fixed pixel positions from the right edge
    base_x = 240  # Base offset from right edge for the rightmost digit
    
    # Centiseconds ones digit (rightmost)
    filters.append(
        f"drawtext=text='{timer_centis_ones}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x}:y={timer_y}"
    )
    
    # Centiseconds tens digit
    filters.append(
        f"drawtext=text='{timer_centis_tens}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 50}:y={timer_y}"
    )
    
    # Colon separator
    filters.append(
        f"drawtext=text='{timer_colon}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 76}:y={timer_y}"
    )
    
    # Seconds ones digit
    filters.append(
        f"drawtext=text='{timer_seconds_ones}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 124}:y={timer_y}"
    )
    
    # Seconds tens digit (only shown when >= 10)
    filters.append(
        f"drawtext=text='{timer_seconds_tens}':fontcolor=white:fontsize={timer_fontsize}:x=w-{base_x + 174}:y={timer_y}:enable='{show_seconds_tens}'"
    )
    
    # Add split overlays (if splits are provided)
    if splits:
        # Get start split timestamp for calculating relative times
        start_split_timestamp = splits.get('start', '').strip()
        if start_split_timestamp:
            try:
                start_split_seconds = timestamp_to_seconds(start_split_timestamp)
                
                # Process LP and PP splits at the bottom
                # All top splits appear at the same time (when the later of LP/PP occurs)
                # Center them with a gap of 800 pixels between them, then shift left
                # LP on the left of center, PP on the right of center
                
                # First, find the maximum timestamp between LP and PP
                lp_appears_at = None
                pp_appears_at = None
                lp_has_value = False
                pp_has_value = False
                
                if 'LP' in splits and splits['LP'].strip() and splits['LP'].strip() != "00:00:00.000":
                    try:
                        lp_seconds = timestamp_to_seconds(splits['LP'].strip())
                        lp_appears_at = lp_seconds - start_seconds
                        lp_has_value = True
                    except:
                        pass
                
                if 'PP' in splits and splits['PP'].strip() and splits['PP'].strip() != "00:00:00.000":
                    try:
                        pp_seconds = timestamp_to_seconds(splits['PP'].strip())
                        pp_appears_at = pp_seconds - start_seconds
                        pp_has_value = True
                    except:
                        pass
                
                # Determine when all top splits should appear (max of LP and PP)
                # If both are missing, show them at the start split time
                top_splits_appear_at = None
                if lp_appears_at is not None and pp_appears_at is not None:
                    top_splits_appear_at = max(lp_appears_at, pp_appears_at)
                elif lp_appears_at is not None:
                    top_splits_appear_at = lp_appears_at
                elif pp_appears_at is not None:
                    top_splits_appear_at = pp_appears_at
                else:
                    # Both are missing, show NP 5 seconds before the end (or at timer_offset if video is too short)
                    if duration > 5:
                        top_splits_appear_at = duration - 5
                    else:
                        top_splits_appear_at = timer_offset
                
                if top_splits_appear_at is not None:
                    # Animation parameters for sliding from bottom (same for all bottom splits)
                    slide_duration = 0.4  # Faster slide-in
                    slide_start = top_splits_appear_at
                    slide_end = top_splits_appear_at + slide_duration
                    
                    # Y positions (offset from bottom, above timer/title bar)
                    # Use fixed offset from bottom for all timestamps to ensure perfect alignment
                    timestamp_y_offset = 72  # All timestamps at same height: 72px above timer bar
                    label_y_offset = 113  # All labels at same height: 113px above timer bar (41px above timestamps)
                    
                    # Bottom positions for PP and LP
                    # PP on the left, LP on the right
                    pp_x_offset = 1315  # Offset from left edge
                    lp_x_offset = 1630  # Offset from right edge

                    x_positions = {
                        'PP': f'w-tw-{pp_x_offset}',  # Left side
                        'LP': f'w-tw-{lp_x_offset}'   # Right side (width - offset)
                    }
                    
                    # Process LP and PP splits with their výstřik splits
                    # Each LP/PP gets 2 lines: top line (small font) for výstřik, bottom line (large font) for LP/PP
                    top_splits = ['LP', 'PP']
                    for split_name in top_splits:
                        # Determine if this split has a value
                        has_value = (split_name == 'LP' and lp_has_value) or (split_name == 'PP' and pp_has_value)
                        
                        # Get the main split timestamp (LP or PP)
                        main_split_formatted = None
                        if has_value and split_name in splits:
                            split_timestamp = splits[split_name].strip()
                            if split_timestamp and split_timestamp != "00:00:00.000":
                                try:
                                    split_seconds = timestamp_to_seconds(split_timestamp)
                                    relative_seconds = split_seconds - start_split_seconds
                                    seconds_part = int(relative_seconds)
                                    centiseconds_part = int((relative_seconds - seconds_part) * 100)
                                    main_split_formatted = f"{seconds_part}\\:{centiseconds_part:02d}"
                                except:
                                    pass
                        
                        if main_split_formatted is None:
                            main_split_formatted = "NP"
                        
                        # Get the výstřik timestamp for this split
                        vystrik_key = f'výstřik_{split_name}'
                        vystrik_formatted = None
                        if vystrik_key in splits:
                            vystrik_timestamp = splits[vystrik_key].strip()
                            if vystrik_timestamp and vystrik_timestamp != "00:00:00.000":
                                try:
                                    vystrik_seconds = timestamp_to_seconds(vystrik_timestamp)
                                    vystrik_relative_seconds = vystrik_seconds - start_split_seconds
                                    vystrik_seconds_part = int(vystrik_relative_seconds)
                                    vystrik_centiseconds_part = int((vystrik_relative_seconds - vystrik_seconds_part) * 100)
                                    vystrik_formatted = f"{vystrik_seconds_part}\\:{vystrik_centiseconds_part:02d}"
                                except:
                                    pass
                        
                        # Build the two lines
                        split_name_safe = ff_escape_text(split_name)
                        vystrik_name_safe = ff_escape_text('Výstřik')
                        
                        # Bottom line: "LP 12:34" or "PP 12:34"
                        main_combined = f"{split_name_safe} {main_split_formatted}"
                        
                        # Top line: "Výstřik 12:34" (only if výstřik exists)
                        if vystrik_formatted:
                            vystrik_combined = f"{vystrik_name_safe} {vystrik_formatted}"
                        else:
                            vystrik_combined = None
                        
                        # Animation parameters
                        final_slide_out_start = duration - 1.0
                        final_slide_out_end = duration
                        
                        # Y position for main split (bottom line) - all timestamps aligned
                        y_pos_main = f"if(lt(t\\,{slide_start})\\,h+5\\,if(lt(t\\,{slide_end})\\,h+5-((t-{slide_start})/{slide_duration})*({5+timestamp_y_offset})\\,if(lt(t\\,{final_slide_out_start})\\,h-{timestamp_y_offset}\\,if(gte(t\\,{final_slide_out_end})\\,h+100\\,h-{timestamp_y_offset}+((t-{final_slide_out_start})/1.0)*({100+timestamp_y_offset})))))"
                        
                        # Y position for výstřik (top line) - all labels aligned
                        y_pos_vystrik = f"if(lt(t\\,{slide_start})\\,h+5\\,if(lt(t\\,{slide_end})\\,h+5-((t-{slide_start})/{slide_duration})*({5+label_y_offset})\\,if(lt(t\\,{final_slide_out_start})\\,h-{label_y_offset}\\,if(gte(t\\,{final_slide_out_end})\\,h+100\\,h-{label_y_offset}+((t-{final_slide_out_start})/1.0)*({100+label_y_offset})))))"
                        
                        # X position based on split name (PP left, LP right)
                        x_pos = x_positions[split_name]
                        
                        # Main split line (bottom, larger font)
                        filters.append(
                            f"drawtext=text='{main_combined}':fontcolor=white:fontsize=60:x={x_pos}:y={y_pos_main}:enable='gte(t\\,{slide_start})'"
                        )
                        
                        # Výstřik line (top, smaller font) - only if it exists
                        if vystrik_combined:
                            filters.append(
                                f"drawtext=text='{vystrik_combined}':fontcolor=white:fontsize=30:x={x_pos}:y={y_pos_vystrik}:enable='gte(t\\,{slide_start})'"
                            )
                    
                    # Process koš, voda, rozdělovač splits at the bottom
                    # These appear left of the timer: rozdělovač (leftmost), voda (middle), koš (closest to timer)
                    bottom_split_names = [
                        ('rozdělovač', 'Rozdělovač', 960),   # (key, display_name, x_offset_from_timer)
                        ('voda', 'Voda', 780),
                        ('koš', 'Koš', 600)
                    ]
                    
                    for split_key, display_name, x_offset_from_timer in bottom_split_names:
                        if split_key in splits:
                            split_timestamp = splits[split_key].strip()
                            # Check if it's a valid non-zero timestamp
                            if split_timestamp and split_timestamp != "00:00:00.000":
                                try:
                                    # Convert absolute timestamp to seconds
                                    split_seconds = timestamp_to_seconds(split_timestamp)
                                    # Calculate relative to "start" split
                                    relative_seconds = split_seconds - start_split_seconds
                                    
                                    # Calculate when this split should appear (relative to začátek)
                                    split_appears_at = split_seconds - start_seconds
                                    
                                    # Format with colon separator (XX:YY where YY is centiseconds)
                                    seconds_part = int(relative_seconds)
                                    centiseconds_part = int((relative_seconds - seconds_part) * 100)
                                    split_formatted = f"{seconds_part}\\:{centiseconds_part:02d}"
                                    
                                    # Escape the display name
                                    split_name_safe = ff_escape_text(display_name)
                                    
                                    # Animation parameters for this split
                                    split_slide_duration = 0.4  # Faster slide-in
                                    split_slide_start = split_appears_at
                                    split_slide_end = split_appears_at + split_slide_duration
                                    
                                    # Y position for timestamp: slide in from bottom, stay visible, then slide out 1s before end
                                    final_slide_out_start = duration - 1.0
                                    final_slide_out_end = duration
                                    # Use same Y offset as LP/PP timestamps for perfect alignment
                                    y_pos_timestamp = f"if(lt(t\\,{split_slide_start})\\,h+5\\,if(lt(t\\,{split_slide_end})\\,h+5-((t-{split_slide_start})/{split_slide_duration})*({5+timestamp_y_offset})\\,if(lt(t\\,{final_slide_out_start})\\,h-{timestamp_y_offset}\\,if(gte(t\\,{final_slide_out_end})\\,h+100\\,h-{timestamp_y_offset}+((t-{final_slide_out_start})/1.0)*({100+timestamp_y_offset})))))"
                                    
                                    # Y position for label: use same Y offset as Výstřik labels for perfect alignment
                                    y_pos_label = f"if(lt(t\\,{split_slide_start})\\,h+5\\,if(lt(t\\,{split_slide_end})\\,h+5-((t-{split_slide_start})/{split_slide_duration})*({5+label_y_offset})\\,if(lt(t\\,{final_slide_out_start})\\,h-{label_y_offset}\\,if(gte(t\\,{final_slide_out_end})\\,h+100\\,h-{label_y_offset}+((t-{final_slide_out_start})/1.0)*({100+label_y_offset})))))"
                                    
                                    # X position: left of timer (timer is at w-164, so position relative to that)
                                    x_pos = f"w-{x_offset_from_timer}-tw"
                                    
                                    # Timestamp (larger font)
                                    filters.append(
                                        f"drawtext=text='{split_formatted}':fontcolor=white:fontsize=60:x={x_pos}:y={y_pos_timestamp}:enable='gte(t\\,{split_slide_start})'"
                                    )
                                    
                                    # Label above timestamp (smaller font)
                                    filters.append(
                                        f"drawtext=text='{split_name_safe}':fontcolor=white:fontsize=30:x={x_pos}:y={y_pos_label}:enable='gte(t\\,{split_slide_start})'"
                                    )
                                except:
                                    continue
            except:
                pass
    
    # Join all filters
    vf = ",".join(filters)
    
    # Check if logo file exists and prepare command accordingly
    logo_path = os.path.join(os.path.dirname(os.path.abspath(input_file)), "sdh_zbraslav-logo.png")
    script_dir_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdh_zbraslav-logo.png")
    
    # Try both locations: same directory as video, or same directory as script
    if os.path.exists(logo_path):
        use_logo = True
        logo_file = logo_path
    elif os.path.exists(script_dir_logo):
        use_logo = True
        logo_file = script_dir_logo
    else:
        use_logo = False
    
    if use_logo:
        # Build complex filter with logo overlay
        # [0:v] is the main video, [1:v] is the logo
        # Apply all filters to main video first, then overlay the logo at the end
        complex_filter = f"[0:v]{vf}[vid];[1:v]scale=95:-1[logo];[vid][logo]overlay=W-w-30:H-h-20"
        
        cmd = [
            "ffmpeg",
            "-ss", start, "-i", input_file,
            "-loop", "1", "-i", logo_file,
            "-t", str(duration),
            "-filter_complex", complex_filter,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "18",
            "-c:a", "aac", "-b:a", "128k",
            "-avoid_negative_ts", "make_zero",
            "-fflags", "+genpts",
            "-y", out
        ]
    else:
        # No logo, use simple filter
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
  Each line has 12 fields:
  title;začátek;start;koš;voda;kohout;rozdělovač;výstřik_LP;výstřik_PP;LP;PP;konec
  
  Example:
  Zbraslav;00:00:11.900;00:00:16.901;00:00:17.400;00:00:18.151;00:00:18.402;00:00:19.151;00:00:19.651;00:00:19.901;00:00:20.400;00:00:20.901;00:00:21.901

Output:
  - Creates 'out-parts/' folder in same directory as source video
  - Overlays title (bottom left) and timer (bottom right) on each segment
  - Auto-joins segments into final video

Examples:
  python3 firetimer-cutvid.py -s myvideo.mp4 -t timestamps.txt
  python3 firetimer-cutvid.py --source recording.mp4 --times segments.txt -z
        """
    )
    parser.add_argument("--source", "-s", required=True, help="Video source: local MP4 file path")
    parser.add_argument("--times", "-t", required=True, help="Timestamps file")
    parser.add_argument("-z", action="store_true", help="Sort by final time (max of LP/PP) and add placement labels (1.místo, 2.místo, etc.)")
    args = parser.parse_args()

    check_deps()

    # Check if source file exists
    if not os.path.exists(args.source):
        print(f"ERROR: source file does not exist: {args.source}")
        sys.exit(1)

    # Create out-parts directory based on video location
    parts_dir = prepare_parts_dir(args.source)
    print(f"📁 Cut videos will be saved to: {parts_dir}")

    # Validate timestamps file first
    print("🔍 Validating timestamps file...")
    is_valid, warnings = validate_timestamps_file(args.times)
    
    if not is_valid:
        print("\n⚠️  VALIDATION WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print("\n❌ Validation failed. Please fix the issues in the timestamps file and try again.")
        sys.exit(1)
    
    print("✅ Validation passed!\n")

    segments = parse_timestamps_file(args.times)
    if not segments:
        print("No valid segments found. Exiting.")
        sys.exit(1)

    # Sort segments by final time only if -z flag is set
    if args.z:
        def get_final_time(seg_data):
            """Calculate the final time for sorting (max of LP and PP relative to start)
            Returns (is_valid, final_time) where is_valid indicates if all required splits exist
            """
            title, start, end, splits = seg_data
            
            # Check if title indicates NP (e.g., "n na PP", "n na LP", or starts with "NP")
            title_lower = title.lower().strip()
            if title_lower.startswith('n na ') or title_lower.startswith('np'):
                return (False, float('inf'))
            
            if not splits or 'start' not in splits or not splits['start'].strip():
                # Missing start split - invalid
                return (False, float('inf'))
            
            try:
                start_split_seconds = timestamp_to_seconds(splits['start'].strip())
                
                lp_seconds = 0
                pp_seconds = 0
                lp_valid = False
                pp_valid = False
                
                if 'LP' in splits and splits['LP'].strip():
                    try:
                        lp_timestamp = splits['LP'].strip()
                        # Check if it's not zero
                        if lp_timestamp != "00:00:00.000":
                            lp_seconds = timestamp_to_seconds(lp_timestamp)
                            lp_valid = True
                    except:
                        pass
                
                if 'PP' in splits and splits['PP'].strip():
                    try:
                        pp_timestamp = splits['PP'].strip()
                        # Check if it's not zero
                        if pp_timestamp != "00:00:00.000":
                            pp_seconds = timestamp_to_seconds(pp_timestamp)
                            pp_valid = True
                    except:
                        pass
                
                # If both LP and PP are missing or zero - invalid
                # OR if only one is valid (one pipe only) - also invalid
                if not lp_valid and not pp_valid:
                    return (False, float('inf'))
                
                # If only one pipe has a valid time, treat as invalid (NP)
                if lp_valid != pp_valid:  # XOR: one is valid, the other is not
                    return (False, float('inf'))
                
                # Both pipes have valid times - valid placement
                # Return the relative time of max(LP, PP) from start
                max_split = max(lp_seconds, pp_seconds)
                return (True, max_split - start_split_seconds)
            except:
                return (False, float('inf'))
        
        # Sort segments by final time (lowest to highest), invalid ones go last
        segments_sorted = sorted(segments, key=get_final_time)
        print(f"📊 Sorted {len(segments_sorted)} segments by final time (lowest to highest)")
        
        # Count valid segments for placement numbering
        valid_count = sum(1 for seg in segments_sorted if get_final_time(seg)[0])
        print(f"   Valid segments: {valid_count}, Invalid (NP): {len(segments_sorted) - valid_count}")
    else:
        # No sorting - keep original order from file
        segments_sorted = segments
        print(f"📋 Processing {len(segments_sorted)} segments in original order")

    parts = []
    placement_counter = 1  # Counter for valid placements
    invalid_counter = 999  # Counter for invalid segments (counts down from 999)
    
    for i, seg_data in enumerate(segments_sorted):
        title, start, end, splits = seg_data
        
        # Check if segment has valid splits for placement
        if args.z:
            is_valid, _ = get_final_time(seg_data)
        else:
            is_valid = True  # All segments are valid when not sorting
        
        # Determine label and order prefix based on -z flag and validity
        if args.z:
            if is_valid:
                label = f"{placement_counter}.místo"
                order_prefix = placement_counter
                placement_counter += 1
            else:
                label = "NP"
                order_prefix = invalid_counter
                invalid_counter -= 1
        else:
            # Without -z, show attack number (in original order)
            label = f"{i + 1}.útok"
            order_prefix = i + 1
            order_prefix = i + 1
        
        part = cut_and_label_segment(args.source, title, start, end, i, parts_dir, splits, label, order_prefix)
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
