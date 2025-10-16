#!/usr/bin/env python3
import sys
import yt_dlp

def download_video(url, filename="video.mp4"):
    ydl_opts = {
        "outtmpl": filename,
        "format": "bestvideo+bestaudio/best"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./download.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    download_video(url)
