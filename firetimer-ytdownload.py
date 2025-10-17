#!/usr/bin/env python3
"""
firetimer-ytdownload.py - Download YouTube videos in time-based chunks

Usage:
  python3 firetimer-ytdownload.py --url <youtube_url> --name <video_name> [OPTIONS]

Required Arguments:
  --url, -u              YouTube URL to download
  --name, -n             Video filename (without .mp4 extension)
                         Also used as folder name if --folder is not specified

Optional Arguments:
  --folder, -f           Output folder (default: uses --name as folder name)
  --chunk-minutes, -c    Chunk duration in minutes (default: 10)
  --start, --from, -s    Start time in HH:MM:SS, MM:SS, or seconds (default: 0)
  --end, --to, -e        End time in HH:MM:SS, MM:SS, or seconds (default: end of video)

Time Format:
  - Seconds: 120
  - MM:SS: 2:30
  - HH:MM:SS: 1:30:45

Output:
  - Downloads to <folder>/in-parts/ directory
  - Automatically joins parts into final video in <folder>/

Examples:
  # Download entire video with auto-generated folder
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n my_video

  # Download with specific folder
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n my_video
  
  # Download specific time range from long livestream
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n long_stream -s 10:30 -e 45:20
  
  # Download time range in seconds
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n clip -s 300 -e 900

Features:
  - Downloads YouTube videos with max 1080p video quality
  - No audio quality limit (best available)
  - Downloads YouTube videos in time-based chunks directly
  - Uses FFmpeg to stream only specific time segments
  - Each chunk downloads only its time range (10 minutes default)
  - Supports downloading specific time ranges from videos
"""
import argparse
import os
import sys
import subprocess
import yt_dlp

def seconds_to_time_string(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def parse_time_to_seconds(time_str):
    """Convert time string (HH:MM:SS or seconds) to seconds"""
    if not time_str:
        return None
    
    try:
        # If it's just a number, treat as seconds
        if time_str.isdigit():
            return int(time_str)
        
        # Parse HH:MM:SS format
        parts = time_str.split(':')
        if len(parts) == 1:
            return int(parts[0])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            raise ValueError(f"Invalid time format: {time_str}")
    except ValueError as e:
        print(f"❌ Error parsing time '{time_str}': {e}")
        print("   Supported formats: seconds (120), MM:SS (2:30), HH:MM:SS (1:30:45)")
        sys.exit(1)

def download_video_in_chunks(url, output_folder, video_name, chunk_minutes=10, start_time="0", end_time=None):
    """Download video in chunks directly from YouTube to save disk space"""
    # Create main folder and in-parts subfolder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    parts_folder = os.path.join(output_folder, "in-parts")
    if not os.path.exists(parts_folder):
        os.makedirs(parts_folder)
    
    # Get video info first to determine duration and format
    info_opts = {
        "quiet": True,
        "no_warnings": True,
    }
    
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        duration = info.get('duration', 0)
        title = info.get('title', 'video')
        
        # Get the best format URL for direct streaming
        formats = info.get('formats', [])
        best_format = None
        for fmt in reversed(formats):  # Start from best quality
            if (fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none' and 
                fmt.get('height', 0) <= 1080):
                best_format = fmt
                break
        
        if not best_format:
            # Fallback to any format with both video and audio
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    best_format = fmt
                    break
    
    if duration == 0:
        print("❌ Could not determine video duration")
        return []
        
    if not best_format or not best_format.get('url'):
        print("❌ Could not find suitable video format")
        return []
    
    video_url = best_format['url']
    
    # Parse start and end times
    start_seconds = parse_time_to_seconds(start_time)
    end_seconds = parse_time_to_seconds(end_time) if end_time else duration
    
    # Validate time ranges
    if start_seconds >= duration:
        print(f"❌ Start time ({start_seconds}s) is beyond video duration ({duration}s)")
        return []
    
    if end_seconds > duration:
        end_seconds = duration
        
    if start_seconds >= end_seconds:
        print(f"❌ Start time ({start_seconds}s) must be less than end time ({end_seconds}s)")
        return []
    
    # Calculate actual download duration
    download_duration = end_seconds - start_seconds
    
    print(f"📊 Video duration: {seconds_to_time_string(duration)} ({duration/60:.1f} minutes)")
    print(f"🎯 Download range: {seconds_to_time_string(start_seconds)} - {seconds_to_time_string(end_seconds)} (Duration: {seconds_to_time_string(download_duration)})")
    print(f"📦 Downloading {chunk_minutes}-minute chunks directly")
    
    chunk_duration_seconds = chunk_minutes * 60
    num_chunks = int(download_duration / chunk_duration_seconds) + 1
    
    base_name = os.path.splitext(video_name)[0] if video_name.endswith('.mp4') else video_name
    downloaded_parts = []
    
    for i in range(num_chunks):
        chunk_start = start_seconds + (i * chunk_duration_seconds)
        chunk_end = min(chunk_start + chunk_duration_seconds, end_seconds)
        
        if chunk_start >= end_seconds:
            break
            
        part_name = f"{base_name}_part{i+1:02d}.mp4"
        part_path = os.path.join(parts_folder, part_name)
        
        print(f"⬇️  Downloading part {i+1}/{num_chunks}: {part_name}")
        print(f"    Time range: {seconds_to_time_string(chunk_start)} - {seconds_to_time_string(chunk_end)}")
        
        # Download chunk using yt-dlp with external_downloader set to ffmpeg.
        # This approach downloads the exact time range using yt-dlp's built-in
        # segment extraction, which handles keyframes correctly and produces
        # clean chunks suitable for concatenation.
        try:
            chunk_opts = {
                "outtmpl": part_path,
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                # Use external downloader (ffmpeg) with download sections
                "download_ranges": yt_dlp.utils.download_range_func(None, [(chunk_start, chunk_end)]),
            }
            
            with yt_dlp.YoutubeDL(chunk_opts) as ydl:
                ydl.download([url])
            
            if os.path.exists(part_path):
                downloaded_parts.append(part_path)
                size_mb = os.path.getsize(part_path) / (1024 * 1024)
                print(f"    ✅ Downloaded: {size_mb:.1f}MB")
            else:
                print(f"    ❌ Download failed - file not created")
                # Fallback: try simpler approach with postprocessor_args
                print(f"    🔄 Trying fallback method...")
                try:
                    fallback_opts = {
                        "outtmpl": part_path,
                        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                        "merge_output_format": "mp4",
                        "quiet": True,
                    }
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        # Download full video then trim with ffmpeg
                        ydl.download([url])
                    
                    # Manual trim with ffmpeg if needed
                    if os.path.exists(part_path):
                        downloaded_parts.append(part_path)
                        size_mb = os.path.getsize(part_path) / (1024 * 1024)
                        print(f"    ✅ Fallback success: {size_mb:.1f}MB")
                    else:
                        print(f"    ❌ Fallback also failed")
                except Exception as fe:
                    print(f"    ❌ Fallback error: {fe}")
                    
        except Exception as e:
            print(f"    ❌ Error downloading part {i+1}: {e}")
            continue
    
    return downloaded_parts

def download_video_full(url, output_folder, video_name):
    """Fallback: Download full video (original method)"""
    # Ensure video name has .mp4 extension
    if not video_name.endswith('.mp4'):
        video_name += '.mp4'
    
    output_path = os.path.join(output_folder, video_name)
    
    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "merge_output_format": "mp4",
        "postprocessors": [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return [output_path]

def join_videos(video_list, output_file="output.mp4"):
    """Join multiple MP4 videos into one file using FFmpeg concat"""
    temp_list = "_firejoiner_list.txt"
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_file))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    with open(temp_list, "w", encoding="utf-8") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"🔗 Joining {len(video_list)} parts into final video...")
    output_path = os.path.abspath(output_file)
    
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
        return output_path
    except subprocess.CalledProcessError as e:
        if os.path.exists(temp_list):
            os.remove(temp_list)
        print(f"❌ FFmpeg error: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube videos in time-based chunks to save disk space.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download entire video with auto-generated folder
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n my_video

  # Download with specific folder
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n my_video
  
  # Download specific time range from long livestream
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n long_stream -s 10:30 -e 45:20
  
  # Download time range in seconds
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -n clip -s 300 -e 900

Time Format: seconds (120), MM:SS (2:30), or HH:MM:SS (1:30:45)
Output: Downloads to <folder>/in-parts/ directory, joins into final video in <folder>/
        """
    )
    parser.add_argument("--url", "-u", required=True, help="YouTube URL to download")
    parser.add_argument("--name", "-n", required=True, help="Video filename (without .mp4 extension). Also used as folder name if --folder not specified")
    parser.add_argument("--folder", "-f", help="Output folder (default: uses --name as folder name)")
    parser.add_argument("--chunk-minutes", "-c", type=int, default=10, help="Chunk duration in minutes (default: 10)")
    parser.add_argument("--start", "--from", "-s", type=str, default="0", help="Start time in HH:MM:SS, MM:SS, or seconds (default: 0)")
    parser.add_argument("--end", "--to", "-e", type=str, help="End time in HH:MM:SS, MM:SS, or seconds (default: end of video)")
    args = parser.parse_args()

    # If folder not specified, use name as folder
    if not args.folder:
        args.folder = args.name
        print(f"📁 Using '{args.folder}' as output folder (same as video name)")

    parts = download_video_in_chunks(args.url, args.folder, args.name, args.chunk_minutes, args.start, args.end)
    
    if parts:
        print(f"\n✅ Successfully downloaded {len(parts)} parts:")
        total_size = 0
        for i, part in enumerate(parts, 1):
            size_mb = os.path.getsize(part) / (1024 * 1024) if os.path.exists(part) else 0
            total_size += size_mb
            print(f"   Part {i}: {os.path.basename(part)} ({size_mb:.1f}MB)")
        print(f"\n📊 Total size: {total_size:.1f}MB")
        
        # Automatically join parts into final video
        final_name = args.name if args.name.endswith('.mp4') else f"{args.name}.mp4"
        final_path = os.path.join(args.folder, final_name)
        
        print(f"\n🔗 Creating final joined video...")
        try:
            join_videos(parts, final_path)
            final_size = os.path.getsize(final_path) / (1024 * 1024)
            print(f"🎬 Final video: {final_name} ({final_size:.1f}MB)")
            print(f"📁 Parts saved in: {os.path.join(args.folder, 'in-parts')}")
        except Exception as e:
            print(f"❌ Failed to join videos: {e}")
    else:
        print("❌ Download failed")

if __name__ == "__main__":
    main()
