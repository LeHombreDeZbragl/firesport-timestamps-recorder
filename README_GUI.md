# Video Timestamp Recorder

A comprehensive GUI application for playing MP4 videos and recording timestamped segments with millisecond precision.

## Features

✅ **Embedded Video Player** - Play MP4 videos directly in the app  
✅ **Millisecond Precision** - Record timestamps with .mmm accuracy  
✅ **Keyboard Shortcuts** - Press `S` for start, `E` for end, `Space` for play/pause  
✅ **Visual Controls** - Buttons for all functions + progress slider  
✅ **Segment Titling** - Enter custom titles for each segment  
✅ **Live Preview** - See all recorded segments in real-time  
✅ **Export Function** - Save to text file in required format  

## Installation

### 1. Install Dependencies

```bash
# Install VLC media player (required)
sudo apt update
sudo apt install vlc

# Install Python packages
pip install -r requirements_gui.txt
```

### 2. Run the Application

```bash
python3 video_timestamp_recorder.py
```

## Usage

### Basic Workflow
1. **Load Video**: Click "📁 Load Video" to select an MP4 file
2. **Play Video**: Click "▶️ Play" or press `Space`
3. **Record Start**: Press `S` key or click "🟢 Save Start" when you want to mark the beginning
4. **Record End**: Press `E` key or click "🔴 Save End" when you want to mark the end
5. **Enter Title**: Type a title for the segment in the popup dialog
6. **Repeat**: Continue recording more segments
7. **Export**: Click "💾 Export Timestamps" to save to file

### Keyboard Shortcuts
- `S` - Save start timestamp
- `E` - Save end timestamp  
- `Space` - Play/Pause video
- Mouse - Click and drag progress slider to seek

### Output Format
The exported file contains segments in the exact format you requested:
```
title1;00:00:03.360;00:00:18.360
title2;00:00:27.360;00:00:42.360
title3;00:01:15.120;00:01:45.890
```

## GUI Layout

```
┌─ Video Timestamp Recorder ────────────────────────┐
│ ┌─ Video Player Area (Black) ───────────────────┐ │
│ │                                               │ │
│ │           Video plays here                    │ │
│ │                                               │ │
│ └───────────────────────────────────────────────┘ │
│ Current Time: 00:01:23.456                        │
│ ████████████████░░░░░░░░░░ [Progress Slider]      │
│                                                   │
│ ┌─ Video Controls ──────────────────────────────┐ │
│ │ [📁 Load] [▶️ Play] [⏹️ Stop]                 │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ ┌─ Timestamp Recording ─────────────────────────┐ │
│ │ [🟢 Start(S)] [🔴 End(E)] [🗑️ Clear] [💾 Export] │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ Start: 00:01:15.120    Segments: 3               │
│                                                   │
│ ┌─ Recorded Segments ───────────────────────────┐ │
│ │  1. Opening Scene                             │ │
│ │     00:00:03.360 - 00:00:18.360               │ │
│ │                                               │ │
│ │  2. Main Action                               │ │
│ │     00:00:27.360 - 00:00:42.360               │ │
│ └───────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────┘
```

## Technical Details

- **Video Engine**: VLC media player backend
- **GUI Framework**: PyQt5
- **Timestamp Precision**: Milliseconds (±1ms accuracy)
- **Supported Formats**: MP4, AVI, MOV, MKV
- **Export Format**: UTF-8 text file with semicolon separators

## Troubleshooting

### VLC Not Found
```bash
# Ubuntu/Debian
sudo apt install vlc

# macOS
brew install vlc

# Windows
# Download from https://www.videolan.org/vlc/
```

### PyQt5 Installation Issues
```bash
# Alternative installation
pip install PyQt5-Qt5==5.15.2
pip install PyQt5-sip==12.11.0
pip install PyQt5==5.15.7
```

### Permission Issues
```bash
# Make script executable
chmod +x video_timestamp_recorder.py
```

## Example Output File

```
Opening Scene;00:00:03.360;00:00:18.360
Character Introduction;00:00:27.360;00:00:42.360
Main Dialogue;00:01:15.120;00:01:45.890
Action Sequence;00:02:30.450;00:03:15.220
Closing Credits;00:04:45.100;00:05:30.000
```

This format is perfect for use with your other video processing scripts!