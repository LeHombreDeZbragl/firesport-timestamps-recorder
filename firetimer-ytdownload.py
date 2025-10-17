#!/usr/bin/env python3
"""
Usage:
  python3 firetimer-ytdownload.py --url <youtube_url> --folder <output_folder> --name <video_name>

Features:
  - Downloads YouTube videos with max 1080p video quality
  - No audio quality limit (best available)
  - Downloads YouTube videos in time-based chunks directly
  - Uses FFmpeg to stream only specific time segments
  - Each chunk downloads only its time range (10 minutes default)

Examples:
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n my_video
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n long_stream
"""
import argparse
import os
import sys
import subprocess
import yt_dlp

def download_video_in_chunks(url, output_folder, video_name, chunk_minutes=10):
    """Download video in chunks directly from YouTube to save disk space"""
    # Create main folder and parts subfolder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    parts_folder = os.path.join(output_folder, "parts")
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
    print(f"📊 Video duration: {duration/60:.1f} minutes")
    print(f"📦 Downloading {chunk_minutes}-minute chunks directly")
    
    chunk_duration_seconds = chunk_minutes * 60
    num_chunks = int(duration / chunk_duration_seconds) + 1
    
    base_name = os.path.splitext(video_name)[0] if video_name.endswith('.mp4') else video_name
    downloaded_parts = []
    
    for i in range(num_chunks):
        start_time = i * chunk_duration_seconds
        end_time = min((i + 1) * chunk_duration_seconds, duration)
        
        if start_time >= duration:
            break
            
        part_name = f"{base_name}_part{i+1:02d}.mp4"
        part_path = os.path.join(parts_folder, part_name)
        
        print(f"⬇️  Downloading part {i+1}/{num_chunks}: {part_name}")
        print(f"    Time range: {start_time/60:.1f}min - {end_time/60:.1f}min")
        
        # Download chunk directly using ffmpeg with the video URL
        cmd = [
            "ffmpeg",
            "-i", video_url,         # Input from YouTube URL
            "-ss", str(start_time),  # Seek to start time (after input for accuracy)
            "-t", str(end_time - start_time),  # Duration of chunk
            "-c", "copy",            # Copy streams (no re-encoding)
            "-avoid_negative_ts", "make_zero",
            "-f", "mp4",             # Output format
            "-y", part_path          # Output file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(part_path):
                downloaded_parts.append(part_path)
                size_mb = os.path.getsize(part_path) / (1024 * 1024)
                print(f"    ✅ Downloaded: {size_mb:.1f}MB")
            else:
                print(f"    ❌ Failed to download part: {result.stderr}")
                # If direct streaming fails, fall back to yt-dlp for this chunk
                print(f"    🔄 Trying fallback method...")
                try:
                    fallback_opts = {
                        "outtmpl": part_path,
                        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                        "merge_output_format": "mp4",
                        "postprocessor_args": [
                            "-ss", str(start_time),
                            "-t", str(end_time - start_time)
                        ],
                        "quiet": True,
                    }
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        ydl.download([url])
                    
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
    parser = argparse.ArgumentParser(description="Download YouTube videos in time-based chunks to save disk space.")
    parser.add_argument("--url", "-u", required=True, help="YouTube URL to download")
    parser.add_argument("--folder", "-f", required=True, help="Output folder (will be created if it doesn't exist)")
    parser.add_argument("--name", "-n", required=True, help="Video filename (without .mp4 extension)")
    parser.add_argument("--chunk-minutes", "-c", type=int, default=10, help="Chunk duration in minutes (default: 10)")
    args = parser.parse_args()

    parts = download_video_in_chunks(args.url, args.folder, args.name, args.chunk_minutes)
    
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
            print(f"📁 Parts saved in: {os.path.join(args.folder, 'parts')}")
        except Exception as e:
            print(f"❌ Failed to join videos: {e}")
    else:
        print("❌ Download failed")

if __name__ == "__main__":
    main()
