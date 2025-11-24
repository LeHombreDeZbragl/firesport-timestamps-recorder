#!/bin/bash
# FIRE Project Environment Activation Script

echo "🔥 FIRE Project Environment Setup"
echo "=================================="

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated"
echo "✅ Python: $(python --version)"
echo "✅ Working directory: $(pwd)"
echo ""

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "
try:
    import yt_dlp
    print('✅ yt-dlp: Available')
except ImportError:
    print('❌ yt-dlp: Missing')

try:
    import PyQt5
    print('✅ PyQt5: Available')
except ImportError:
    print('❌ PyQt5: Missing')

try:
    import vlc
    print('✅ python-vlc: Available')
    print('   VLC version:', vlc.libvlc_get_version().decode())
except ImportError:
    print('❌ python-vlc: Missing')
except Exception as e:
    print('❌ VLC system library issue:', e)
"

echo ""
echo "🎬 Available Scripts:"
echo "===================="
echo "📥 YouTube Downloader (with chunking):"
echo "   python3 firetimer-ytdownload.py -u <URL> -f <folder> -n <name> -c <minutes>"
echo ""
echo "🔗 Video Joiner:"
echo "   python3 firetimer-joinvids.py -f <parts_folder> -O <output.mp4>"
echo ""
echo "✂️  Video Cutter (with timer overlays):"
echo "   python3 firetimer-cutvid.py -i <input.mp4> -t <timestamps.txt> -o <output_folder>"
echo ""
echo "🎮 GUI Timestamp Recorder:"
echo "   python3 video_timestamp_recorder.py"
echo ""
echo "💡 Examples:"
echo "   # Download 6-hour video in 10-minute chunks"
echo "   python3 firetimer-ytdownload.py -u 'https://youtube.com/watch?v=...' -f long_video -n full_stream -c 10"
echo ""
echo "   # Record timestamps with GUI"
echo "   python3 video_timestamp_recorder.py"
echo ""
echo "   # Cut video with timer overlays"
echo "   python3 firetimer-cutvid.py -i full_stream.mp4 -t timestamps.txt -o segments"
echo ""
echo "🚀 Environment ready! Happy video processing! 🔥"