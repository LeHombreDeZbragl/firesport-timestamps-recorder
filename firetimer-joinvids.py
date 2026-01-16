#!/usr/bin/env python3
"""
firetimer-joinvids.py - Join multiple MP4 video parts into a single file

Usage:
  python3 firetimer-joinvids.py --folder <folder_with_parts> [OPTIONS]

Required Arguments:
  --folder, --parts, -f, -p    Folder containing MP4 parts to join
                               (supports both 'in-parts' and 'out-parts')

Optional Arguments:
  --intro, -i                  Optional intro video file (added at beginning)
  --outro, -o                  Optional outro video file (added at end)
  --out, -O                    Output filename (saved one level above folder)
                               If not specified, auto-generates based on folder type:
                               - 'out-parts' → final_out_video.mp4
                               - 'in-parts' → final_in_video.mp4
                               - other → final_video.mp4

Output:
  - Joins all MP4 files in alphabetical order
  - Output saved one level above the parts folder
  - Uses FFmpeg concat with copy mode (no re-encoding, fast!)

Examples:
  # Join parts with auto-generated output filename
  python3 firetimer-joinvids.py -f out-parts
  
  # Join with custom output filename
  python3 firetimer-joinvids.py -f in-parts -O final_video.mp4
  
  # Join with intro and outro
  python3 firetimer-joinvids.py -f out-parts -i intro.mp4 -o outro.mp4 -O complete.mp4

Features:
  - Fast joining using FFmpeg concat (no re-encoding)
  - Alphabetical ordering of parts
  - Optional intro/outro support
  - Auto-detects folder type for intelligent naming
"""

import argparse
import subprocess
import os
import sys

def check_deps():
    import shutil
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH. Install ffmpeg and ensure it's on PATH.")
        sys.exit(1)

def collect_videos(folder):
    if not os.path.exists(folder):
        print(f"ERROR: Folder not found: {folder}")
        sys.exit(1)
    vids = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".mp4")
    ])
    if not vids:
        print(f"No .mp4 files found in {folder}")
        sys.exit(1)
    return vids

def normalize_videos(video_list):
    normalized = []
    temps = []
    for v in video_list:
        temp = v + ".norm.mp4"
        cmd = [
            "ffmpeg",
            "-fflags", "+genpts",
            "-i", v,
            "-map", "0",
            "-c", "copy",
            "-reset_timestamps", "1",
            "-avoid_negative_ts", "make_zero",
            "-max_interleave_delta", "0",
            "-y", temp
        ]
        print(f"🧹 Normalizing timestamps: {os.path.basename(v)}")
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            normalized.append(temp)
            temps.append(temp)
        except subprocess.CalledProcessError:
            if os.path.exists(temp):
                os.remove(temp)
            raise
    return normalized, temps

def join_videos(video_list, output_file="output.mp4"):
    temp_list = "_firejoiner_list.txt"
    normalized_videos, temp_artifacts = normalize_videos(video_list)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_file))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    with open(temp_list, "w", encoding="utf-8") as f:
        for v in normalized_videos:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"🔗 Joining {len(video_list)} parts...")
    output_path = os.path.abspath(output_file)
    print(f"📝 Output path: {output_path}")
    
    cmd = [
        "ffmpeg",
        "-fflags", "+genpts",  # regenerate timestamps to keep DTS monotonic
        "-f", "concat", "-safe", "0",
        "-i", temp_list,
        "-c", "copy",  # Copy streams without re-encoding (much faster!)
        "-avoid_negative_ts", "make_zero",
        "-max_interleave_delta", "0",
        "-y", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Final video saved as: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        print(f"💡 Try checking if the output directory is writable: {output_dir}")
        raise
    finally:
        if os.path.exists(temp_list):
            os.remove(temp_list)
        for t in temp_artifacts:
            if os.path.exists(t):
                os.remove(t)

def main():
    parser = argparse.ArgumentParser(
        description="Join multiple MP4 clips with optional intro/outro.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output:
  - Joins all MP4 files in alphabetical order
  - Auto-generates output filename if not specified:
    * 'out-parts' → final_out_video.mp4
    * 'in-parts' → final_in_video.mp4
    * other → final_video.mp4
  - Saves output one level above parts folder

Examples:
  python3 firetimer-joinvids.py -f out-parts
  python3 firetimer-joinvids.py -f in-parts -O final_video.mp4
  python3 firetimer-joinvids.py -f out-parts -i intro.mp4 -o outro.mp4 -O complete.mp4
        """
    )
    parser.add_argument("--folder", "--parts", "-f", "-p", required=True, help="Folder containing parts (.mp4 files) - supports both 'in-parts' and 'out-parts'.")
    parser.add_argument("--intro", "-i", help="Optional intro video file.")
    parser.add_argument("--outro", "-o", help="Optional outro video file.")
    parser.add_argument("--out", "-O", help="Output filename (will be saved one level above the folder). If not specified, auto-generates based on folder type.")
    args = parser.parse_args()

    check_deps()

    # Auto-generate output filename if not specified
    if args.out:
        output_filename = args.out
    else:
        # Get the parent folder name (one level above the parts folder)
        folder_path = os.path.abspath(args.folder)
        parent_dir = os.path.dirname(folder_path)
        parent_folder_name = os.path.basename(parent_dir)
        output_filename = f"{parent_folder_name}_final.mp4"
        print(f"📝 Auto-generated output filename: {output_filename}")

    # Ensure output filename has .mp4 extension
    if not output_filename.endswith('.mp4'):
        output_filename += '.mp4'

    # Calculate output path - one level above the specified folder
    folder_path = os.path.abspath(args.folder)
    parent_dir = os.path.dirname(folder_path)
    output_path = os.path.join(parent_dir, output_filename)

    # Ensure the output directory exists
    os.makedirs(parent_dir, exist_ok=True)

    print(f"📁 Output will be saved to: {output_path}")

    videos = []
    if args.intro and os.path.exists(args.intro):
        videos.append(args.intro)

    videos.extend(collect_videos(args.folder))

    if args.outro and os.path.exists(args.outro):
        videos.append(args.outro)

    join_videos(videos, output_path)

if __name__ == "__main__":
    main()
