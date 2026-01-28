#!/usr/bin/env python3
"""
video_timestamp_recorder.py - GUI application for marking video timestamps with splits

Description:
  A video player for recording timestamped segments with frame-by-frame precision and split points.
  
Usage:
  python3 video_timestamp_recorder.py

Interface:
  - Load Video: Opens file dialog to select MP4 video
  - Play/Pause: Space bar or button
  - Seek: Click on progress bar or use arrow keys (5 seconds)
  - Frame Navigation:
    * , (comma) - Back 1 frame
    * . (period) - Forward 1 frame
    * Shift+← - Back 10 frames
    * Shift+→ - Forward 10 frames
  
Marking Segments:
  1. Position video at start point → Press W or click "Začátek"
  2. (Optional) Mark up to 9 split points → Press E/S/D/F/G/X/C/V/B
  3. (Optional) Adjust start split with -150ms → Press R
  4. (Optional) Type segment name in the text field → Press N to focus
  5. Position video at end point → Press T or click "Konec"
  5. Segment is automatically saved with name (or auto-generated number)
  6. All segments exported to 'timestamps.txt' in format:
     title;start_time;split1;split2;...;split9;end_time

Keyboard Shortcuts:
  W              - Mark začátek (start)
  E, S, D, F,    - Mark splits 1-9
  G, X, C, V, B
  R              - Subtract 150ms from start split
  T              - Mark konec (end)
  N              - Focus segment name field
  Space          - Play/Pause
  , (comma)      - Back 1 frame
  . (period)     - Forward 1 frame
  Shift+←        - Back 10 frames
  Shift+→        - Forward 10 frames
  ← / →          - Seek backward/forward 5 seconds
  Escape         - Unfocus text fields

Output:
  - timestamps.txt: Segment data for use with firetimer-cutvid.py
  - Format: title;HH:MM:SS.mmm;split1;split2;...;split9;HH:MM:SS.mmm

Requirements:
  - PyQt5: pip install PyQt5
  - python-vlc: pip install python-vlc
  - VLC media player installed on system

Features:
  - Video playback with audio
  - Frame-by-frame precision navigation
  - 9 split points per segment (Czech labels)
  - Live segment editing with editable timestamps
  - Auto-generated segment names (Segment 1, Segment 2, etc.)
  - Inline segment naming without modal dialogs
  - Exports to extended 'timestamps.txt' format with splits
"""

import sys
import os
import time
import re
from datetime import timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QFileDialog, QMessageBox,
                            QTextEdit, QFrame, QSlider, QGroupBox, QLineEdit)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import QShortcut
import vlc

class SelectAllOnFocusLineEdit(QLineEdit):
    """Custom QLineEdit that clears default value or selects all when it gains focus"""
    def focusInEvent(self, event):
        super().focusInEvent(event)
        # If the field contains the default value "0.000", clear it
        if self.text() == "0.000":
            self.clear()
        else:
            # Otherwise, select all text
            self.selectAll()

class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Timestamp Recorder")
        self.setGeometry(100, 100, 1400, 800)
        
        # Video player variables
        vlc_args = [
            '--quiet',                          # Reduce verbose output
            '--no-spu',                         # Disable subtitles
            '--video-on-top',                   # Keep video window on top when focused
            '--no-osd',                         # Disable on-screen display
            '--audio-time-stretch',             # Enable audio time stretching for better sync
            '--avcodec-fast',                   # Use faster decoding
            '--network-caching=1000',           # Network cache in ms
            '--file-caching=300',               # File cache in ms (lower = less latency)
            '--live-caching=300',               # Live cache in ms
            '--clock-jitter=0',                 # No clock jitter
            '--clock-synchro=0',                # Disable clock synchronization adjustments
            '--audio-desync=0'                  # No audio desynchronization
        ]
        
        try:
            self.instance = vlc.Instance(vlc_args)
        except:
            # Fallback with minimal audio disabling
            print("Warning: Using fallback VLC instance with audio disabled")
            self.instance = vlc.Instance(['--no-audio'])
            
        if self.instance is None:
            print("Error: Could not create VLC instance")
            return
            
        self.media_player = self.instance.media_player_new()
        
        self.current_video_path = None
        
        # Timestamp recording variables
        self.start_timestamp = None
        self.split_timestamps = [None] * 9  # 9 split points
        self.segments = []
        self.output_file = "timestamps.txt"
        
        # Split names in Czech
        self.split_names = ['start', 'koš', 'voda', 'kohout', 'rozdělovač', 'výstřik LP', 'výstřik PP', 'LP', 'PP']
        
        # Timer for updating current time display
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_display)
        self.timer.start(250)  # Update every 250ms
        
        self.init_ui()
        self.setup_shortcuts()
        
    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side: Video and controls
        left_layout = QVBoxLayout()
        
        # Video frame
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setMinimumHeight(700)
        self.video_frame.setMinimumWidth(800)
        left_layout.addWidget(self.video_frame, stretch=1)
        
        # Set the video output to the frame
        if sys.platform.startswith('linux'):
            self.media_player.set_xwindow(int(self.video_frame.winId()))
        elif sys.platform == "win32":
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(int(self.video_frame.winId()))
        
        # Time display
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00:00.000")
        self.current_time_label.setFont(QFont("Courier", 16, QFont.Bold))
        self.current_time_label.setStyleSheet("color: blue; padding: 5px;")
        time_layout.addWidget(QLabel("Current Time:"))
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        left_layout.addLayout(time_layout)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        self.progress_slider.sliderMoved.connect(self.slider_moved)
        left_layout.addWidget(self.progress_slider)
        
        # Control buttons
        controls_group = QGroupBox("Video Controls")
        controls_layout = QVBoxLayout(controls_group)
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        
        # First row: Load, Play
        row1_layout = QHBoxLayout()
        self.load_button = QPushButton("📁 Load Video")
        self.load_button.clicked.connect(self.load_video)
        row1_layout.addWidget(self.load_button)
        
        self.play_pause_button = QPushButton("▶️ Play")
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.play_pause_button.setEnabled(False)
        row1_layout.addWidget(self.play_pause_button)
        controls_layout.addLayout(row1_layout)
        
        # Second row: Frame and seek controls
        row2_layout = QHBoxLayout()
        self.seek_back_button = QPushButton("⏪ -5s (←)")
        self.seek_back_button.clicked.connect(self.seek_backward_5s)
        self.seek_back_button.setEnabled(False)
        row2_layout.addWidget(self.seek_back_button)
        
        self.frame_back_button = QPushButton("◀ Frame (,)")
        self.frame_back_button.clicked.connect(self.frame_backward)
        self.frame_back_button.setEnabled(False)
        row2_layout.addWidget(self.frame_back_button)
        
        self.frame_forward_button = QPushButton("▶ Frame (.)")
        self.frame_forward_button.clicked.connect(self.frame_forward)
        self.frame_forward_button.setEnabled(False)
        row2_layout.addWidget(self.frame_forward_button)
        
        self.seek_forward_button = QPushButton("⏩ +5s (→)")
        self.seek_forward_button.clicked.connect(self.seek_forward_5s)
        self.seek_forward_button.setEnabled(False)
        row2_layout.addWidget(self.seek_forward_button)
        controls_layout.addLayout(row2_layout)
        
        left_layout.addWidget(controls_group)
        
        # Add left layout to main layout
        main_layout.addLayout(left_layout, stretch=3)
        
        # Right side: Timestamp recording
        right_layout = QVBoxLayout()
        
        # Timestamp recording controls
        timestamp_group = QGroupBox("Timestamp Recording")
        timestamp_layout = QVBoxLayout(timestamp_group)
        
        # Segment naming input at the top
        naming_layout = QVBoxLayout()
        naming_layout.addWidget(QLabel("Segment Name (N):"))
        
        self.segment_name_input = QLineEdit()
        self.segment_name_input.setPlaceholderText("Enter segment name (optional)")
        self.segment_name_input.returnPressed.connect(self.unfocus_text_fields)
        naming_layout.addWidget(self.segment_name_input)
        timestamp_layout.addLayout(naming_layout)
        
        # Start button with editable time and -150ms button
        start_layout = QHBoxLayout()
        self.start_button = QPushButton("🟢 Začátek (W)")
        self.start_button.clicked.connect(self.save_start_timestamp)
        self.start_button.setEnabled(False)
        self.start_button.setMinimumWidth(120)
        start_layout.addWidget(self.start_button)
        
        self.start_time_input = QLineEdit("00:00:00.000")
        self.start_time_input.setMinimumWidth(120)
        self.start_time_input.setMaximumWidth(120)
        self.start_time_input.setStyleSheet("color: orange;")
        self.start_time_input.textChanged.connect(self.on_start_time_edited)
        start_layout.addWidget(self.start_time_input)
        
        # -150ms button on same line
        self.minus_150_btn = QPushButton("-150ms (R)")
        self.minus_150_btn.setMinimumWidth(100)
        self.minus_150_btn.setMaximumWidth(100)
        self.minus_150_btn.clicked.connect(self.subtract_150ms_from_start)
        start_layout.addWidget(self.minus_150_btn)
        
        timestamp_layout.addLayout(start_layout)
        
        # Split buttons with inline editable time (absolute and relative)
        self.split_buttons = []
        self.split_time_inputs = []
        self.split_relative_inputs = []
        split_keys = ['E', 'S', 'D', 'F', 'G', 'X', 'C', 'V', 'B']
        
        for i in range(9):
            split_layout = QHBoxLayout()
            
            btn = QPushButton(f"{self.split_names[i]} ({split_keys[i]})")
            btn.clicked.connect(lambda checked, idx=i: self.save_split_timestamp(idx))
            btn.setEnabled(False)
            btn.setMinimumWidth(120)
            self.split_buttons.append(btn)
            split_layout.addWidget(btn)
            
            # Absolute time
            time_input = QLineEdit("00:00:00.000")
            time_input.setMinimumWidth(120)
            time_input.setMaximumWidth(120)
            time_input.setStyleSheet("color: orange; font-size: 9pt;")
            time_input.textChanged.connect(lambda text, idx=i: self.on_split_absolute_time_edited(idx, text))
            self.split_time_inputs.append(time_input)
            split_layout.addWidget(time_input)
            
            # Relative time (from split 1 "start") - format: 00.000 (seconds with 3 decimals)
            # Skip relative field for index 0 (start) - it doesn't make sense, it's always 0
            if i == 0:
                # Add placeholder to keep the list indices aligned
                self.split_relative_inputs.append(None)
            else:
                relative_input = SelectAllOnFocusLineEdit("0.000")
                relative_input.setMinimumWidth(100)
                relative_input.setMaximumWidth(100)
                relative_input.setStyleSheet("color: gray; font-size: 9pt;")
                relative_input.editingFinished.connect(lambda idx=i: self.on_split_relative_time_edited(idx, self.split_relative_inputs[idx].text()))
                relative_input.returnPressed.connect(self.unfocus_text_fields)
                self.split_relative_inputs.append(relative_input)
                split_layout.addWidget(relative_input)
            
            timestamp_layout.addLayout(split_layout)
        
        # End button with editable time
        end_layout = QHBoxLayout()
        self.end_button = QPushButton("🔴 Konec (T)")
        self.end_button.clicked.connect(self.save_end_timestamp)
        self.end_button.setEnabled(False)
        self.end_button.setMinimumWidth(150)
        end_layout.addWidget(self.end_button)
        timestamp_layout.addLayout(end_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.clear_all_button = QPushButton("🗑️ Clear All Segments")
        self.clear_all_button.clicked.connect(self.clear_segments)
        action_layout.addWidget(self.clear_all_button)
        
        self.clear_current_button = QPushButton("🧹 Clear")
        self.clear_current_button.clicked.connect(self.clear_current_timestamps)
        action_layout.addWidget(self.clear_current_button)
        
        self.export_button = QPushButton("💾 Export")
        self.export_button.clicked.connect(self.export_timestamps)
        action_layout.addWidget(self.export_button)
        timestamp_layout.addLayout(action_layout)
        
        # Segments count
        self.segments_count_label = QLabel("Segments: 0")
        self.segments_count_label.setStyleSheet("color: blue; font-weight: bold;")
        timestamp_layout.addWidget(self.segments_count_label)
        
        right_layout.addWidget(timestamp_group)
        
        # Segments display
        segments_group = QGroupBox("Recorded Segments")
        segments_layout = QVBoxLayout(segments_group)
        
        self.segments_display = QTextEdit()
        self.segments_display.setReadOnly(False)
        self.segments_display.setFont(QFont("Courier", 9))
        self.segments_display.setPlaceholderText("Timestamps will appear here. You can edit them directly.")
        self.segments_display.textChanged.connect(self.parse_segments_from_text)
        segments_layout.addWidget(self.segments_display)
        
        right_layout.addWidget(segments_group)
        
        # Add right layout to main layout
        main_layout.addLayout(right_layout, stretch=1)
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # W key for start timestamp
        self.start_shortcut = QShortcut(QKeySequence("W"), self)
        self.start_shortcut.activated.connect(self.save_start_timestamp)
        
        # T key for end timestamp
        self.end_shortcut = QShortcut(QKeySequence("T"), self)
        self.end_shortcut.activated.connect(self.save_end_timestamp)
        
        # E, S, D, F, G, X, C, V, B keys for 9 splits
        split_keys = ['E', 'S', 'D', 'F', 'G', 'X', 'C', 'V', 'B']
        self.split_shortcuts = []
        for i, key in enumerate(split_keys):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda idx=i: self.save_split_timestamp(idx))
            self.split_shortcuts.append(shortcut)
        
        # R key for -150ms button
        self.minus_150_shortcut = QShortcut(QKeySequence("R"), self)
        self.minus_150_shortcut.activated.connect(self.subtract_150ms_from_start)
        
        # Space for play/pause
        self.play_shortcut = QShortcut(QKeySequence("Space"), self)
        self.play_shortcut.activated.connect(self.toggle_play_pause)
        
        # Frame navigation shortcuts
        # Comma (,) for frame backward
        self.frame_back_shortcut = QShortcut(QKeySequence(","), self)
        self.frame_back_shortcut.activated.connect(self.frame_backward)
        
        # Period (.) for frame forward
        self.frame_forward_shortcut = QShortcut(QKeySequence("."), self)
        self.frame_forward_shortcut.activated.connect(self.frame_forward)
        
        # Arrow keys for 5-second seek
        self.left_arrow_shortcut = QShortcut(QKeySequence("Left"), self)
        self.left_arrow_shortcut.activated.connect(self.seek_backward_5s)
        
        self.right_arrow_shortcut = QShortcut(QKeySequence("Right"), self)
        self.right_arrow_shortcut.activated.connect(self.seek_forward_5s)
        
        # Shift + Arrow keys for 10-frame jumps
        self.shift_left_shortcut = QShortcut(QKeySequence("Shift+Left"), self)
        self.shift_left_shortcut.activated.connect(self.frame_backward_10)
        
        self.shift_right_shortcut = QShortcut(QKeySequence("Shift+Right"), self)
        self.shift_right_shortcut.activated.connect(self.frame_forward_10)
        
        # N key for focusing name input
        self.name_shortcut = QShortcut(QKeySequence("N"), self)
        self.name_shortcut.activated.connect(self.focus_name_input)
        
        # Escape to unfocus text fields
        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.unfocus_text_fields)
    
    def focus_name_input(self):
        """Focus the segment name input field"""
        self.segment_name_input.setFocus()
        self.segment_name_input.selectAll()
    
    def unfocus_text_fields(self):
        """Unfocus all text fields"""
        self.setFocus()
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to unfocus text fields"""
        focused_widget = self.focusWidget()
        if focused_widget == self.segment_name_input or focused_widget == self.segments_display or \
           focused_widget in [inp for inp in self.split_relative_inputs if inp is not None] or \
           focused_widget in self.split_time_inputs or focused_widget == self.start_time_input:
            self.setFocus()
        super().mousePressEvent(event)
        
    def load_video(self):
        """Load an MP4 video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select MP4 Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.current_video_path = file_path
            media = self.instance.media_new(file_path)
            
            self.media_player.set_media(media)
            
            # Enable controls
            self.play_pause_button.setEnabled(True)
            self.frame_back_button.setEnabled(True)
            self.frame_forward_button.setEnabled(True)
            self.seek_back_button.setEnabled(True)
            self.seek_forward_button.setEnabled(True)
            
            # Enable Začátek button, first split button (start - index 0), LP (index 7), and PP (index 8)
            self.start_button.setEnabled(True)
            for i, btn in enumerate(self.split_buttons):
                if i == 0 or i == 7 or i == 8:  # First split (start), LP, PP
                    btn.setEnabled(True)
                else:
                    btn.setEnabled(False)
            
            # Update window title
            self.setWindowTitle(f"Video Timestamp Recorder (Video Only) - {os.path.basename(file_path)}")
            
            # Parse media to get duration
            media.parse()
            
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.media_player.is_playing():
            self.media_player.pause()
            self.play_pause_button.setText("▶️ Play")
        else:
            self.media_player.play()
            self.play_pause_button.setText("⏸️ Pause")
            
    def stop_video(self):
        """Stop video playback"""
        self.media_player.stop()
        self.play_pause_button.setText("▶️ Play")
        
    def get_frame_duration_ms(self):
        """Get the duration of one frame in milliseconds"""
        default_frame_duration = 1000 / 30  # ~33.33ms
        
        try:
            media = self.media_player.get_media()
            if media:
                media.parse()
                tracks = media.tracks_get()
                for track in tracks:
                    if track.type == vlc.TrackType.video:
                        fps = track.video.frame_rate_num / track.video.frame_rate_den if track.video.frame_rate_den > 0 else 30
                        return 1000 / fps
        except:
            pass
            
        return default_frame_duration
    
    def seek_forward_5s(self):
        """Seek forward 5 seconds"""
        if self.media_player and self.current_video_path:
            current_time = self.media_player.get_time()
            if current_time >= 0:
                new_time = current_time + 5000
                duration = self.media_player.get_length()
                if duration > 0 and new_time < duration:
                    self.media_player.set_time(new_time)
                elif duration > 0:
                    self.media_player.set_time(duration)
    
    def seek_backward_5s(self):
        """Seek backward 5 seconds"""
        if self.media_player and self.current_video_path:
            current_time = self.media_player.get_time()
            if current_time >= 0:
                new_time = max(0, current_time - 5000)
                self.media_player.set_time(new_time)
    
    def frame_forward(self):
        """Move one frame forward"""
        if self.media_player and self.current_video_path:
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            current_time = self.media_player.get_time()
            if current_time >= 0:
                frame_duration = self.get_frame_duration_ms()
                new_time = current_time + int(frame_duration)
                duration = self.media_player.get_length()
                if duration > 0 and new_time < duration:
                    self.media_player.set_time(new_time)
                    
    def frame_backward(self):
        """Move one frame backward"""
        if self.media_player and self.current_video_path:
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            current_time = self.media_player.get_time()
            if current_time >= 0:
                frame_duration = self.get_frame_duration_ms()
                new_time = max(0, current_time - int(frame_duration))
                self.media_player.set_time(new_time)
                
    def frame_forward_10(self):
        """Move 10 frames forward"""
        if self.media_player and self.current_video_path:
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            current_time = self.media_player.get_time()
            if current_time >= 0:
                frame_duration = self.get_frame_duration_ms()
                new_time = current_time + int(frame_duration * 10)
                duration = self.media_player.get_length()
                if duration > 0 and new_time < duration:
                    self.media_player.set_time(new_time)
                    
    def frame_backward_10(self):
        """Move 10 frames backward"""
        if self.media_player and self.current_video_path:
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            current_time = self.media_player.get_time()
            if current_time >= 0:
                frame_duration = self.get_frame_duration_ms()
                new_time = max(0, current_time - int(frame_duration * 10))
                self.media_player.set_time(new_time)
        
    def get_current_timestamp_ms(self):
        """Get current video timestamp in milliseconds"""
        return self.media_player.get_time()
        
    def format_timestamp(self, ms):
        """Convert milliseconds to hh:mm:ss.mmm format"""
        if ms is None:
            return "00:00:00.000"
        
        total_seconds = ms // 1000
        milliseconds = ms % 1000
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        
    def update_time_display(self):
        """Update the current time display and progress slider"""
        if self.media_player and self.current_video_path:
            current_time = self.get_current_timestamp_ms()
            if current_time >= 0:
                self.current_time_label.setText(self.format_timestamp(current_time))
                
                duration = self.media_player.get_length()
                if duration > 0:
                    position = int((current_time / duration) * 1000)
                    self.progress_slider.setValue(position)
                    
    def slider_pressed(self):
        """Handle slider press - pause updates"""
        self.timer.stop()
    
    def slider_moved(self, value):
        """Handle slider movement - update time label preview"""
        duration = self.media_player.get_length()
        if duration > 0:
            position = value / 1000.0
            preview_time_ms = int(duration * position)
            self.current_time_label.setText(self.format_timestamp(preview_time_ms))
        
    def slider_released(self):
        """Handle slider release - seek and resume updates"""
        duration = self.media_player.get_length()
        if duration > 0:
            position = self.progress_slider.value() / 1000.0
            self.media_player.set_position(position)
        self.timer.start()
    
    def on_start_time_edited(self, text):
        """Handle manual edit of start time"""
        try:
            # If field is empty or cleared, reset the start timestamp
            if not text or text.strip() == "":
                self.start_timestamp = None
                self.start_time_input.blockSignals(True)
                self.start_time_input.setText("00:00:00.000")
                self.start_time_input.setStyleSheet("color: orange;")
                self.start_time_input.blockSignals(False)
                # Disable end button and other splits since we don't have a start
                self.end_button.setEnabled(False)
                for i, btn in enumerate(self.split_buttons):
                    if i == 0:  # Keep first split (start) enabled
                        btn.setEnabled(True)
                    else:
                        btn.setEnabled(False)
                # Update relative times
                self.update_all_relative_times()
                return
            
            ms = self.timestamp_to_ms(text)
            if ms == 0:
                # If parsed to 0, treat as reset
                self.start_timestamp = None
                self.start_time_input.blockSignals(True)
                self.start_time_input.setText("00:00:00.000")
                self.start_time_input.setStyleSheet("color: orange;")
                self.start_time_input.blockSignals(False)
                # Disable end button and other splits
                self.end_button.setEnabled(False)
                for i, btn in enumerate(self.split_buttons):
                    if i == 0:  # Keep first split (start) enabled
                        btn.setEnabled(True)
                    else:
                        btn.setEnabled(False)
            elif ms > 0:
                self.start_timestamp = ms
                self.start_time_input.setStyleSheet("color: green; font-weight: bold;")
                # Update relative times for all splits (relative to split 1)
                self.update_all_relative_times()
        except:
            pass
    
    def on_split_absolute_time_edited(self, idx, text):
        """Handle manual edit of split absolute time"""
        try:
            # If field is empty or cleared, reset the split
            if not text or text.strip() == "":
                self.split_timestamps[idx] = None
                self.split_time_inputs[idx].blockSignals(True)
                self.split_time_inputs[idx].setText("00:00:00.000")
                self.split_time_inputs[idx].setStyleSheet("color: orange; font-size: 9pt;")
                self.split_time_inputs[idx].blockSignals(False)
                if self.split_relative_inputs[idx] is not None:
                    self.split_relative_inputs[idx].blockSignals(True)
                    self.split_relative_inputs[idx].setText("0.000")
                    self.split_relative_inputs[idx].blockSignals(False)
                # If this was split 0 (reference), update all relative times
                if idx == 0:
                    self.update_all_relative_times()
                return
            
            ms = self.timestamp_to_ms(text)
            if ms == 0:
                self.split_timestamps[idx] = None
                self.split_time_inputs[idx].blockSignals(True)
                self.split_time_inputs[idx].setText("00:00:00.000")
                self.split_time_inputs[idx].setStyleSheet("color: orange; font-size: 9pt;")
                self.split_time_inputs[idx].blockSignals(False)
                if self.split_relative_inputs[idx] is not None:
                    self.split_relative_inputs[idx].blockSignals(True)
                    self.split_relative_inputs[idx].setText("0.000")
                    self.split_relative_inputs[idx].blockSignals(False)
            elif ms > 0:
                self.split_timestamps[idx] = ms
                # Update relative time (relative to split 1 "start")
                if idx == 0:
                    # Split 1 has no relative field (index 0 is None)
                    # Update all other splits
                    self.update_all_relative_times()
                else:
                    # Calculate relative to split 1 (index 0)
                    if self.split_timestamps[0] is not None:
                        relative_ms = ms - self.split_timestamps[0]
                        relative_sec = relative_ms / 1000.0
                        self.split_relative_inputs[idx].blockSignals(True)
                        self.split_relative_inputs[idx].setText(f"{relative_sec:.3f}")
                        self.split_relative_inputs[idx].blockSignals(False)
        except:
            pass
    
    def on_split_relative_time_edited(self, idx, text):
        """Handle manual edit of split relative time (relative to split 1)"""
        # Skip if this is index 0 (no relative field for start)
        if idx == 0 or self.split_relative_inputs[idx] is None:
            return
            
        try:
            # If field is empty or cleared, reset the split
            if not text or text.strip() == "":
                self.split_timestamps[idx] = None
                self.split_time_inputs[idx].blockSignals(True)
                self.split_time_inputs[idx].setText("00:00:00.000")
                self.split_time_inputs[idx].setStyleSheet("color: orange; font-size: 9pt;")
                self.split_time_inputs[idx].blockSignals(False)
                if self.split_relative_inputs[idx] is not None:
                    self.split_relative_inputs[idx].blockSignals(True)
                    self.split_relative_inputs[idx].setText("0.000")
                    self.split_relative_inputs[idx].blockSignals(False)
                return
            
            # Parse the seconds value (format: "00.000")
            relative_sec = float(text.strip())
            
            # Special handling for LP (index 7) and PP (index 8) when used as start input
            # (only when start_timestamp is None and the LP/PP timestamp is set)
            if (idx == 7 or idx == 8) and self.start_timestamp is None and self.split_timestamps[idx] is not None:
                # Calculate Start timestamp: LP/PP timestamp - relative time
                lp_pp_timestamp = self.split_timestamps[idx]
                calculated_start = lp_pp_timestamp - int(relative_sec * 1000)
                calculated_start = max(0, calculated_start)  # Ensure non-negative
                
                # Set the start split (index 0) timestamp
                self.split_timestamps[0] = calculated_start
                self.split_time_inputs[0].blockSignals(True)
                self.split_time_inputs[0].setText(self.format_timestamp(calculated_start))
                self.split_time_inputs[0].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
                self.split_time_inputs[0].blockSignals(False)
                
                # Calculate Začátek (Start button) timestamp: Start - 5 seconds
                zacat_timestamp = max(0, calculated_start - 5000)
                self.start_timestamp = zacat_timestamp
                self.start_time_input.setText(self.format_timestamp(zacat_timestamp))
                self.start_time_input.setStyleSheet("color: green; font-weight: bold;")
                
                # Enable all buttons since we now have a start
                self.start_button.setEnabled(True)
                self.end_button.setEnabled(True)
                for btn in self.split_buttons:
                    btn.setEnabled(True)
                
                # Update all relative times since we have a new reference point
                self.update_all_relative_times()
                
                # Update the relative time display for the LP/PP that was just set
                self.split_relative_inputs[idx].blockSignals(True)
                self.split_relative_inputs[idx].setText(f"{relative_sec:.3f}")
                self.split_relative_inputs[idx].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
                self.split_relative_inputs[idx].blockSignals(False)
                
                # Update placeholder
                next_num = len(self.segments) + 1
                self.segment_name_input.setPlaceholderText(f"Segment {next_num} (or custom name)")
                
                # Focus the input field
                self.segment_name_input.setFocus()
                return
            
            # Normal case: when start (split 0) is already set, calculate absolute time
            # Calculate absolute time based on split 1 (start)
            if self.split_timestamps[0] is not None:
                # Check if value is 0, reset the split
                if relative_sec == 0:
                    self.split_timestamps[idx] = None
                    self.split_time_inputs[idx].blockSignals(True)
                    self.split_time_inputs[idx].setText("00:00:00.000")
                    self.split_time_inputs[idx].setStyleSheet("color: orange; font-size: 9pt;")
                    self.split_time_inputs[idx].blockSignals(False)
                    return
                
                absolute_ms = self.split_timestamps[0] + int(relative_sec * 1000)
                self.split_timestamps[idx] = absolute_ms
                
                # Update absolute time display
                self.split_time_inputs[idx].blockSignals(True)
                self.split_time_inputs[idx].setText(self.format_timestamp(absolute_ms))
                self.split_time_inputs[idx].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
                self.split_time_inputs[idx].blockSignals(False)
                
                # Update relative time display
                self.split_relative_inputs[idx].blockSignals(True)
                self.split_relative_inputs[idx].setText(f"{relative_sec:.3f}")
                self.split_relative_inputs[idx].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
                self.split_relative_inputs[idx].blockSignals(False)
        except:
            pass
    
    def update_all_relative_times(self):
        """Update relative time displays for all splits (relative to split 1)"""
        # Split 1 (index 0) is the reference point
        if self.split_timestamps[0] is None:
            # No reference point, reset all relatives (skip index 0)
            for idx in range(1, 9):
                if self.split_relative_inputs[idx] is not None:
                    self.split_relative_inputs[idx].blockSignals(True)
                    self.split_relative_inputs[idx].setText("0.000")
                    self.split_relative_inputs[idx].blockSignals(False)
            return
        
        # Calculate others relative to split 1 (skip index 0 - no relative field for start)
        for idx in range(1, 9):
            if self.split_relative_inputs[idx] is not None and self.split_timestamps[idx] is not None:
                relative_ms = self.split_timestamps[idx] - self.split_timestamps[0]
                relative_sec = relative_ms / 1000.0
                self.split_relative_inputs[idx].blockSignals(True)
                self.split_relative_inputs[idx].setText(f"{relative_sec:.3f}")
                self.split_relative_inputs[idx].blockSignals(False)
    
    def on_end_time_edited(self):
        """Handle manual edit of end time - not used for timestamp, just display"""
        # No special handling needed for end time display
        return
        
    def save_start_timestamp(self):
        """Save the current timestamp as start time (Začátek)"""
        if not self.current_video_path:
            return
            
        self.start_timestamp = self.get_current_timestamp_ms()
        if self.start_timestamp >= 0:
            formatted_time = self.format_timestamp(self.start_timestamp)
            self.start_time_input.setText(formatted_time)
            self.start_time_input.setStyleSheet("color: green; font-weight: bold;")
            self.end_button.setEnabled(True)
            
            # Enable all split buttons
            for btn in self.split_buttons:
                btn.setEnabled(True)
            
            # Reset splits
            self.split_timestamps = [None] * 9
            for time_input in self.split_time_inputs:
                time_input.setText("00:00:00.000")
            
            # Reset relative time inputs
            for i, relative_input in enumerate(self.split_relative_inputs):
                if relative_input is not None:  # Skip index 0 which is None
                    relative_input.setText("0.000")
            
            # Update placeholder
            next_num = len(self.segments) + 1
            self.segment_name_input.setPlaceholderText(f"Segment {next_num} (or custom name)")
            
            # Focus the input field
            self.segment_name_input.setFocus()
    
    def subtract_150ms_from_start(self):
        """Subtract 150 milliseconds from the first split (start) timestamp"""
        if self.split_timestamps[0] is not None and self.split_timestamps[0] > 0:
            new_timestamp = max(0, self.split_timestamps[0] - 150)
            self.split_timestamps[0] = new_timestamp
            
            # Update absolute time display
            self.split_time_inputs[0].blockSignals(True)
            self.split_time_inputs[0].setText(self.format_timestamp(new_timestamp))
            self.split_time_inputs[0].blockSignals(False)
            
            # Update all relative times since the reference changed
            self.update_all_relative_times()
    
    def save_split_timestamp(self, split_index):
        """Save the current timestamp as a split point"""
        if not self.current_video_path:
            return
        
        split_timestamp = self.get_current_timestamp_ms()
        if split_timestamp < 0:
            return
        
        # Special handling for LP (index 7) and PP (index 8) when in initial state
        # (only when start_timestamp is None)
        if (split_index == 7 or split_index == 8) and self.start_timestamp is None:
            # Save the timestamp
            self.split_timestamps[split_index] = split_timestamp
            formatted_time = self.format_timestamp(split_timestamp)
            
            # Block signals to prevent textChanged from resetting the field
            self.split_time_inputs[split_index].blockSignals(True)
            self.split_time_inputs[split_index].setText(formatted_time)
            self.split_time_inputs[split_index].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
            self.split_time_inputs[split_index].blockSignals(False)
            
            # Clear and focus on relative time field for manual entry
            if self.split_relative_inputs[split_index] is not None:
                self.split_relative_inputs[split_index].blockSignals(True)
                self.split_relative_inputs[split_index].setText("")
                self.split_relative_inputs[split_index].blockSignals(False)
                self.split_relative_inputs[split_index].setFocus()
                self.split_relative_inputs[split_index].selectAll()
            return
        
        # Special handling for split 0 (start) - automatically derive začátek if not set
        if split_index == 0:
            if self.start_timestamp is None:
                # First time setting start split - automatically derive začátek
                # Začátek = start - 5 seconds
                derived_start = max(0, split_timestamp - 5000)  # Subtract 5 seconds (5000ms)
                self.start_timestamp = derived_start
                self.start_time_input.setText(self.format_timestamp(derived_start))
                self.start_button.setEnabled(True)  # Now enable začátek button for manual adjustment
            
            # Save the split timestamp
            self.split_timestamps[split_index] = split_timestamp
            formatted_time = self.format_timestamp(split_timestamp)
            self.split_time_inputs[split_index].setText(formatted_time)
            self.split_time_inputs[split_index].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
            
            # No relative time field for split 0 (start)
            # (split_relative_inputs[0] is None)
            
            # Enable all other split buttons and end button
            for btn in self.split_buttons:
                btn.setEnabled(True)
            self.end_button.setEnabled(True)
            
            # Update all other splits since the reference changed
            self.update_all_relative_times()
            
            # Update placeholder
            next_num = len(self.segments) + 1
            self.segment_name_input.setPlaceholderText(f"Segment {next_num} (or custom name)")
            
            # Focus the input field
            self.segment_name_input.setFocus()
        else:
            # Other splits - require start_timestamp to be set
            if self.start_timestamp is None:
                return
            
            if split_timestamp > self.start_timestamp:
                self.split_timestamps[split_index] = split_timestamp
                formatted_time = self.format_timestamp(split_timestamp)
                self.split_time_inputs[split_index].setText(formatted_time)
                self.split_time_inputs[split_index].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
                
                # Calculate relative to split 1
                if self.split_timestamps[0] is not None and self.split_relative_inputs[split_index] is not None:
                    relative_ms = split_timestamp - self.split_timestamps[0]
                    relative_sec = relative_ms / 1000.0
                    self.split_relative_inputs[split_index].setText(f"{relative_sec:.3f}")
                    self.split_relative_inputs[split_index].setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
                elif self.split_relative_inputs[split_index] is not None:
                    # No reference point yet
                    self.split_relative_inputs[split_index].setText("0.000")
                    self.split_relative_inputs[split_index].setStyleSheet("color: gray; font-size: 9pt;")
        
    def save_end_timestamp(self):
        """Save the current timestamp as end time and create segment"""
        if not self.current_video_path:
            return
            
        if self.start_timestamp is None:
            return
            
        end_timestamp = self.get_current_timestamp_ms()
        if end_timestamp >= 0:
            if end_timestamp <= self.start_timestamp:
                return
            
            # Find the highest timestamp among all splits
            highest_split_timestamp = None
            for split_ts in self.split_timestamps:
                if split_ts is not None:
                    if highest_split_timestamp is None or split_ts > highest_split_timestamp:
                        highest_split_timestamp = split_ts
            
            # Adjust end timestamp if needed
            if highest_split_timestamp is not None:
                time_diff = end_timestamp - highest_split_timestamp
                if time_diff < 5000:  # Less than 5 seconds
                    end_timestamp = highest_split_timestamp + 5000
                
            # Get title from input field or use default
            title = self.segment_name_input.text().strip()
            if not title:
                segment_num = len(self.segments) + 1
                title = f"Segment {segment_num}"
            
            segment = {
                'title': title,
                'start': self.start_timestamp,
                'splits': self.split_timestamps.copy(),
                'end': end_timestamp
            }
            self.segments.append(segment)
            
            # Update display
            self.update_segments_display()
            
            # Reset for next segment
            self.start_timestamp = None
            self.split_timestamps = [None] * 9
            self.start_time_input.setText("00:00:00.000")
            self.end_button.setEnabled(False)
            
            # Restore initial state: enable Začátek, first split (start), LP, and PP
            self.start_button.setEnabled(True)
            for i, btn in enumerate(self.split_buttons):
                if i == 0 or i == 7 or i == 8:  # First split (start), LP, PP
                    btn.setEnabled(True)
                else:
                    btn.setEnabled(False)
            
            # Reset split inputs
            for time_input in self.split_time_inputs:
                time_input.setText("00:00:00.000")
                time_input.setStyleSheet("color: orange; font-size: 9pt;")
            
            # Reset relative time inputs
            for i, relative_input in enumerate(self.split_relative_inputs):
                if relative_input is not None:  # Skip index 0 which is None
                    relative_input.setText("0.000")
                    relative_input.setStyleSheet("color: gray; font-size: 9pt;")
            
            # Clear the input field
            self.segment_name_input.clear()
            
            # Auto-increment if using default naming
            if title.startswith("Segment "):
                next_num = len(self.segments) + 1
                self.segment_name_input.setPlaceholderText(f"Segment {next_num} (or custom name)")
            
    def update_segments_display(self):
        """Update the segments display"""
        self.segments_count_label.setText(f"Segments: {len(self.segments)}")
        
        display_text = ""
        for i, segment in enumerate(self.segments, 1):
            start_str = self.format_timestamp(segment['start'])
            end_str = self.format_timestamp(segment['end'])
            
            # Build split string
            splits_str = ""
            for split in segment.get('splits', [None] * 8):
                if split is not None:
                    splits_str += ";" + self.format_timestamp(split)
                else:
                    splits_str += ";00:00:00.000"
            
            display_text += f"{i:2d}. {segment['title']}\n"
            display_text += f"    {start_str}{splits_str};{end_str}\n\n"
            
        # Temporarily disconnect signal to prevent infinite loop
        self.segments_display.textChanged.disconnect()
        self.segments_display.setText(display_text)
        self.segments_display.textChanged.connect(self.parse_segments_from_text)
        
    def parse_segments_from_text(self):
        """Parse segments from the text editor content"""
        text = self.segments_display.toPlainText()
        new_segments = []
        
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^\s*\d+\.\s*', line):
                title_match = re.match(r'^\s*\d+\.\s*(.*)', line)
                if title_match:
                    title = title_match.group(1).strip()
                    
                    if i + 1 < len(lines):
                        timestamp_line = lines[i + 1].strip()
                        parts = timestamp_line.split(';')
                        
                        if len(parts) >= 11:
                            try:
                                start_ms = self.timestamp_to_ms(parts[0])
                                end_ms = self.timestamp_to_ms(parts[10])
                                
                                splits = []
                                for j in range(1, 10):
                                    split_ms = self.timestamp_to_ms(parts[j])
                                    if split_ms == 0:
                                        splits.append(None)
                                    else:
                                        splits.append(split_ms)
                                
                                if title and start_ms >= 0 and end_ms > start_ms:
                                    new_segments.append({
                                        'title': title,
                                        'start': start_ms,
                                        'splits': splits,
                                        'end': end_ms
                                    })
                            except:
                                pass
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        if new_segments != self.segments:
            self.segments = new_segments
            self.segments_count_label.setText(f"Segments: {len(self.segments)}")
    
    def timestamp_to_ms(self, timestamp_str):
        """Convert timestamp string HH:MM:SS.mmm to milliseconds"""
        try:
            parts = timestamp_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1])
            
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            return total_ms
        except:
            return -1
        
    def clear_current_timestamps(self):
        """Clear current timestamp fields and reset to initial state"""
        # Reset timestamps
        self.start_timestamp = None
        self.split_timestamps = [None] * 9
        
        # Reset input fields
        self.start_time_input.setText("00:00:00.000")
        self.start_time_input.setStyleSheet("color: orange;")
        self.segment_name_input.clear()
        
        # Reset split inputs
        for time_input in self.split_time_inputs:
            time_input.setText("00:00:00.000")
            time_input.setStyleSheet("color: orange; font-size: 9pt;")
        
        # Reset relative time inputs
        for i, relative_input in enumerate(self.split_relative_inputs):
            if relative_input is not None:  # Skip index 0 which is None
                relative_input.setText("0.000")
                relative_input.setStyleSheet("color: gray; font-size: 9pt;")
        
        # Restore initial state: enable Začátek, first split (start), LP, and PP
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)
        for i, btn in enumerate(self.split_buttons):
            if i == 0 or i == 7 or i == 8:  # First split (start), LP, PP
                btn.setEnabled(True)
            else:
                btn.setEnabled(False)
        
        # Update placeholder
        next_num = len(self.segments) + 1
        self.segment_name_input.setPlaceholderText(f"Segment {next_num} (or custom name)")
        
    def clear_segments(self):
        """Clear all recorded segments"""
        if self.segments:
            reply = QMessageBox.question(
                self, "Clear Segments", 
                f"Are you sure you want to clear all {len(self.segments)} segments?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.segments.clear()
                self.start_timestamp = None
                self.split_timestamps = [None] * 9
                self.start_time_input.setText("00:00:00.000")
                self.start_time_input.setStyleSheet("color: orange;")
                self.end_button.setEnabled(False)
                
                # Restore initial state: enable Začátek, first split (start), LP, and PP
                self.start_button.setEnabled(True)
                for i, btn in enumerate(self.split_buttons):
                    if i == 0 or i == 7 or i == 8:  # First split (start), LP, PP
                        btn.setEnabled(True)
                    else:
                        btn.setEnabled(False)
                
                # Reset split inputs
                for time_input in self.split_time_inputs:
                    time_input.setText("00:00:00.000")
                    time_input.setStyleSheet("color: orange; font-size: 9pt;")
                
                # Reset relative time inputs
                for i, relative_input in enumerate(self.split_relative_inputs):
                    if relative_input is not None:  # Skip index 0 which is None
                        relative_input.setText("0.000")
                        relative_input.setStyleSheet("color: gray; font-size: 9pt;")
                
                self.update_segments_display()
                
    def export_timestamps(self):
        """Export timestamps to file"""
        if not self.segments:
            QMessageBox.warning(self, "Warning", "No segments to export!")
            return
        
        default_filename = "timestamps.txt"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Timestamps", default_filename, "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for segment in self.segments:
                        start_str = self.format_timestamp(segment['start'])
                        end_str = self.format_timestamp(segment['end'])
                        
                        # Build split string
                        splits_str = ""
                        for split in segment.get('splits', [None] * 8):
                            if split is not None:
                                splits_str += ";" + self.format_timestamp(split)
                            else:
                                splits_str += ";00:00:00.000"
                        
                        f.write(f"{segment['title']};{start_str}{splits_str};{end_str}\n")
                        
                QMessageBox.information(
                    self, "Export Successful", 
                    f"Timestamps exported to:\n{file_path}\n\n{len(self.segments)} segments saved."
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export timestamps:\n{str(e)}")

    def closeEvent(self, event):
        """Handle application close event for cleanup."""
        if hasattr(self, 'media_player') and self.media_player:
            self.media_player.stop()
            self.media_player.release()
        if hasattr(self, 'instance') and self.instance:
            self.instance.release()
        event.accept()

def main():
    app = QApplication(sys.argv)

    # Check for VLC
    try:
        vlc.Instance()
    except Exception as e:
        QMessageBox.critical(
            None, "VLC Error", 
            "VLC media player is required but not found.\n\n"
            "Please install VLC and python-vlc:\n"
            "pip install python-vlc\n\n"
            f"Error: {str(e)}"
        )
        sys.exit(1)

    player = VideoPlayer()
    player.show()

    # Ensure proper cleanup on exit
    exit_code = app.exec_()
    del player
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
