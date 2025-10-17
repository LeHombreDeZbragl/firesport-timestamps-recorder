#!/usr/bin/env python3
"""
Usage:
  python3 firetimer-ytdownload.py --url <youtube_url> --folder <output_folder> --name <video_name>

Examples:
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n my_video
  python3 firetimer-ytdownload.py -u https://youtube.com/watch?v=xyz -f downloads -n game1
"""
import argparse
import os
import sys
import yt_dlp

def download_video(url, output_folder, video_name):
    # Create folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Ensure video name has .mp4 extension
    if not video_name.endswith('.mp4'):
        video_name += '.mp4'
    
    # Set output path
    output_path = os.path.join(output_folder, video_name)
    
    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",  # Force MP4 output
        "postprocessors": [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    print(f"✅ Video downloaded to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Download video from YouTube URL to specified folder.")
    parser.add_argument("--url", "-u", required=True, help="YouTube URL to download")
    parser.add_argument("--folder", "-f", required=True, help="Output folder (will be created if it doesn't exist)")
    parser.add_argument("--name", "-n", required=True, help="Video filename (without .mp4 extension)")
    args = parser.parse_args()

    download_video(args.url, args.folder, args.name)

if __name__ == "__main__":
    main()
