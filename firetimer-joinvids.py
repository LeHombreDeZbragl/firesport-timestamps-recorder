#!/usr/bin/env python3
"""
Usage:
  python3 firetimer-joinvids.py --folder <folder_with_parts> --out <output.mp4> [--intro intro.mp4] [--outro outro.mp4]

Short parameters: -f, -i, -o, -O

Example:
  python3 firetimer-joinvids.py -f parts -O final.mp4
  python3 firetimer-joinvids.py -f parts -i intro.mp4 -o outro.mp4 -O final.mp4
  
Output video will be saved one level above the specified folder.
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

def join_videos(video_list, output_file="output.mp4"):
    temp_list = "_firejoiner_list.txt"
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_file))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    with open(temp_list, "w", encoding="utf-8") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"🔗 Joining {len(video_list)} parts...")
    output_path = os.path.abspath(output_file)
    print(f"📝 Output path: {output_path}")
    
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", temp_list,
        "-c", "copy",  # Copy streams without re-encoding (much faster!)
        "-y", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        os.remove(temp_list)
        print(f"✅ Final video saved as: {output_path}")
    except subprocess.CalledProcessError as e:
        os.remove(temp_list)
        print(f"❌ FFmpeg error: {e}")
        print(f"💡 Try checking if the output directory is writable: {output_dir}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Join multiple mp4 clips with optional intro/outro.")
    parser.add_argument("--folder", "-f", required=True, help="Folder containing parts (.mp4 files).")
    parser.add_argument("--intro", "-i", help="Optional intro video file.")
    parser.add_argument("--outro", "-o", help="Optional outro video file.")
    parser.add_argument("--out", "-O", required=True, help="Output filename (will be saved one level above the folder)")
    args = parser.parse_args()

    check_deps()

    # Ensure output filename has .mp4 extension
    output_filename = args.out
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
