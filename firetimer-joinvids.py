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
import json

def check_deps():
    import shutil
    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH. Install ffmpeg and ensure it's on PATH.")
        sys.exit(1)

SUPPORTED_FORMATS = {'.mp4', '.mov'}

def collect_videos(folder):
    if not os.path.exists(folder):
        print(f"ERROR: Folder not found: {folder}")
        sys.exit(1)
    vids = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f.lower())[1] in SUPPORTED_FORMATS
    ])
    if not vids:
        print(f"No supported video files ({', '.join(sorted(SUPPORTED_FORMATS))}) found in {folder}")
        sys.exit(1)
    return vids

def get_video_dimensions(path):
    """Return (width, height) of the first video stream using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return stream["width"], stream["height"]

def get_video_codec(path):
    """Return the video codec name (e.g. 'hevc', 'h264') using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip().lower()

def normalize_videos(video_list):
    normalized = []
    temps = []
    for v in video_list:
        temp = v + ".norm.mp4"
        cmd = [
            "ffmpeg",
            "-fflags", "+genpts",
            "-i", v,
            "-map", "0:v",
            "-map", "0:a",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-max_interleave_delta", "0",
            "-y", temp
        ]
        print(f"🧹 Normalizing timestamps: {os.path.basename(v)}")
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            normalized.append(temp)
            temps.append(temp)
        except subprocess.CalledProcessError as e:
            if os.path.exists(temp):
                os.remove(temp)
            print(f"❌ FFmpeg error normalizing {os.path.basename(v)}:")
            if e.stderr:
                print(e.stderr)
            raise
    return normalized, temps

def join_videos(video_list, output_file="output.mp4"):
    output_dir = os.path.dirname(os.path.abspath(output_file))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.abspath(output_file)

    needs_encode = any(not v.lower().endswith('.mp4') for v in video_list)
    hevc_detected = False
    if not needs_encode:
        codecs = [get_video_codec(v) for v in video_list]
        hevc_detected = any(c in {'hevc', 'h265'} for c in codecs)
        needs_encode = hevc_detected

    if needs_encode:
        n = len(video_list)
        # Use the first clip's dimensions as the target.
        # Scale + pad everything else to match so concat doesn't choke on
        # mixed portrait/landscape clips (common with iPhone footage).
        target_w, target_h = get_video_dimensions(video_list[0])
        if hevc_detected:
            print(f"ℹ️  HEVC streams detected — re-encoding all {n} clips to H.264 ({target_w}×{target_h})...")
            print("    (HEVC files from phones embed absolute device timestamps; stream copy cannot fix them)")
        else:
            print(f"⚠️  Non-MP4 files detected — re-encoding all {n} clips to {target_w}×{target_h}...")
        print(f"📝 Output path: {output_path}")

        cmd = ["ffmpeg"]
        for v in video_list:
            cmd += ["-i", v]

        # Scale each clip to the target size; pad with black if aspect ratio differs
        filter_parts = []
        for i in range(n):
            filter_parts.append(
                f"[{i}:v]scale={target_w}:{target_h}:"
                f"force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
            )
        concat_inputs = "".join(f"[v{i}][{i}:a]" for i in range(n))
        filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=1[v][a]")
        filter_complex = ";".join(filter_parts)

        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "medium",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-ar", "48000",
            "-ac", "2",
            "-y", output_path
        ]
    else:
        # All native MP4 — fast path: stream-copy without normalization
        temp_list = "_firejoiner_list.txt"
        try:
            with open(temp_list, "w", encoding="utf-8") as f:
                for v in video_list:
                    f.write(f"file '{os.path.abspath(v)}'\n")

            print(f"🔗 Joining {len(video_list)} parts (fast copy)...")
            print(f"📝 Output path: {output_path}")

            cmd = [
                "ffmpeg",
                "-f", "concat", "-safe", "0",
                "-i", temp_list,
                "-c", "copy",
                "-y", output_path
            ]
            subprocess.run(cmd, check=True)
            print(f"✅ Final video saved as: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg error: {e}")
            raise
        finally:
            if os.path.exists(temp_list):
                os.remove(temp_list)
        return

    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Final video saved as: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        raise

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
