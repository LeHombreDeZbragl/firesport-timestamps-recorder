#!/usr/bin/env python3
"""
video_timestamp_recorder.py - GUI application for marking video timestamps

Description:
  A video-only player for recording timestamped segments with frame-by-frame precision.
  Audio is disabled for better performance and stability.
  
Usage:
  python3 video_timestamp_recorder.py

Interface:
  - Load Video: Opens file dialog to select MP4 video
  - Play/Pause: Space bar or button
  - Seek: Click on progress bar or use arrow keys
  - Frame Navigation:
    * , (comma) - Back 1 frame
    * . (period) - Forward 1 frame
    * Shift+← - Back 10 frames
    * Shift+→ - Forward 10 frames
  
Marking Segments:
  1. Position video at start point → Press S or click "Start Segment"
  2. (Optional) Type segment name in the text field → Press N to focus
  3. Position video at end point → Press E or click "End Segment"
  4. Segment is automatically saved with name (or auto-generated number)
  5. All segments exported to 'timestamps.txt' in format:
     title;start_time;end_time

Keyboard Shortcuts:
  S              - Mark start of segment
  E              - Mark end of segment
  N              - Focus segment name field
  Space          - Play/Pause
  , (comma)      - Back 1 frame
  . (period)     - Forward 1 frame
  Shift+←        - Back 10 frames
  Shift+→        - Forward 10 frames
  ← / →          - Seek backward/forward 5 seconds

Output:
  - timestamps.txt: Segment data for use with firetimer-cutvid.py
  - Format: title;HH:MM:SS.mmm;HH:MM:SS.mmm

Requirements:
  - PyQt5: pip install PyQt5
  - python-vlc: pip install python-vlc
  - VLC media player installed on system

Features:
  - Video-only playback (audio disabled for stability)
  - Frame-by-frame precision navigation
  - Live segment editing in text area
  - Auto-generated segment names (Segment 1, Segment 2, etc.)
  - Inline segment naming without modal dialogs
  - Exports to simple 'timestamps.txt' format
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

class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Timestamp Recorder (Video Only)")
        self.setGeometry(100, 100, 1200, 800)
        
        # Video player variables - video only, no audio
        vlc_args = [
            '--quiet',           # Reduce verbose output
            '--no-audio',        # Disable all audio
            '--aout=dummy',      # Use dummy audio output
            '--no-spu',          # Disable subtitles
            '--video-on-top',    # Keep video window on top when focused
            '--no-osd'           # Disable on-screen display
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
        self.segments = []
        self.output_file = "timestamps.txt"
        
        # Timer for updating current time display
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_display)
        self.timer.start(250)  # Update every 250ms (less frequent to reduce interference)
        
        self.init_ui()
        self.setup_shortcuts()
        
    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Video frame
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setMinimumHeight(400)
        main_layout.addWidget(self.video_frame)
        
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
        main_layout.addLayout(time_layout)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.sliderPressed.connect(self.slider_pressed)
        self.progress_slider.sliderReleased.connect(self.slider_released)
        main_layout.addWidget(self.progress_slider)
        
        # Control buttons
        controls_group = QGroupBox("Video Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.load_button = QPushButton("📁 Load Video")
        self.load_button.clicked.connect(self.load_video)
        controls_layout.addWidget(self.load_button)
        
        self.play_pause_button = QPushButton("▶️ Play")
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.play_pause_button.setEnabled(False)
        controls_layout.addWidget(self.play_pause_button)
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.clicked.connect(self.stop_video)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)
        
        # Frame navigation controls
        self.frame_back_button = QPushButton("⏪ Frame Back (,)")
        self.frame_back_button.clicked.connect(self.frame_backward)
        self.frame_back_button.setEnabled(False)
        self.frame_back_button.setToolTip("Move one frame backward\n• Comma (,) or Left arrow: 1 frame back\n• Shift+Left arrow: 10 frames back")
        controls_layout.addWidget(self.frame_back_button)
        
        self.frame_forward_button = QPushButton("⏩ Frame Forward (.)")
        self.frame_forward_button.clicked.connect(self.frame_forward)
        self.frame_forward_button.setEnabled(False)
        self.frame_forward_button.setToolTip("Move one frame forward\n• Period (.) or Right arrow: 1 frame forward\n• Shift+Right arrow: 10 frames forward")
        controls_layout.addWidget(self.frame_forward_button)
        
        controls_layout.addStretch()
        main_layout.addWidget(controls_group)
        
        # Timestamp recording controls
        timestamp_group = QGroupBox("Timestamp Recording")
        timestamp_layout = QVBoxLayout(timestamp_group)
        
        # Button row
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🟢 Save Start (S)")
        self.start_button.clicked.connect(self.save_start_timestamp)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.end_button = QPushButton("🔴 Save End (E)")
        self.end_button.clicked.connect(self.save_end_timestamp)
        self.end_button.setEnabled(False)
        button_layout.addWidget(self.end_button)
        
        self.clear_button = QPushButton("🗑️ Clear Segments")
        self.clear_button.clicked.connect(self.clear_segments)
        button_layout.addWidget(self.clear_button)
        
        self.export_button = QPushButton("💾 Export Timestamps")
        self.export_button.clicked.connect(self.export_timestamps)
        button_layout.addWidget(self.export_button)
        
        timestamp_layout.addLayout(button_layout)
        
        # Segment naming input
        naming_layout = QHBoxLayout()
        naming_layout.addWidget(QLabel("Segment Name:"))
        
        self.segment_name_input = QLineEdit()
        self.segment_name_input.setPlaceholderText("Enter segment name (optional)")
        self.segment_name_input.setToolTip("Enter a custom name for the segment, or leave empty for auto-naming.\nPress Enter to save segment with this name.\nPress N to focus this field.")
        self.segment_name_input.returnPressed.connect(self.save_end_timestamp)  # Allow Enter key to save
        naming_layout.addWidget(self.segment_name_input)
        
        timestamp_layout.addLayout(naming_layout)
        
        timestamp_layout.addStretch()
        main_layout.addWidget(timestamp_group)
        
        # Status display
        status_layout = QHBoxLayout()
        self.start_time_label = QLabel("Start: Not set")
        self.start_time_label.setStyleSheet("color: green; font-weight: bold;")
        status_layout.addWidget(self.start_time_label)
        
        self.segments_count_label = QLabel("Segments: 0")
        self.segments_count_label.setStyleSheet("color: blue; font-weight: bold;")
        status_layout.addWidget(self.segments_count_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        # Segments display
        segments_group = QGroupBox("Recorded Segments")
        segments_layout = QVBoxLayout(segments_group)
        
        self.segments_display = QTextEdit()
        self.segments_display.setMaximumHeight(150)
        self.segments_display.setReadOnly(False)  # Make editable
        self.segments_display.setFont(QFont("Courier", 10))
        self.segments_display.setPlaceholderText("Timestamps will appear here. You can edit them directly.")
        self.segments_display.textChanged.connect(self.parse_segments_from_text)
        segments_layout.addWidget(self.segments_display)
        
        main_layout.addWidget(segments_group)
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # S key for start timestamp
        self.start_shortcut = QShortcut(QKeySequence("S"), self)
        self.start_shortcut.activated.connect(self.save_start_timestamp)
        
        # E key for end timestamp
        self.end_shortcut = QShortcut(QKeySequence("E"), self)
        self.end_shortcut.activated.connect(self.save_end_timestamp)
        
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
        
        # Arrow keys for frame navigation (alternative)
        self.left_arrow_shortcut = QShortcut(QKeySequence("Left"), self)
        self.left_arrow_shortcut.activated.connect(self.frame_backward)
        
        self.right_arrow_shortcut = QShortcut(QKeySequence("Right"), self)
        self.right_arrow_shortcut.activated.connect(self.frame_forward)
        
        # Shift + Arrow keys for 10-frame jumps
        self.shift_left_shortcut = QShortcut(QKeySequence("Shift+Left"), self)
        self.shift_left_shortcut.activated.connect(self.frame_backward_10)
        
        self.shift_right_shortcut = QShortcut(QKeySequence("Shift+Right"), self)
        self.shift_right_shortcut.activated.connect(self.frame_forward_10)
        
        # N key for focusing name input (helpful for quick naming)
        self.name_shortcut = QShortcut(QKeySequence("N"), self)
        self.name_shortcut.activated.connect(self.focus_name_input)
    
    def focus_name_input(self):
        """Focus the segment name input field"""
        self.segment_name_input.setFocus()
        self.segment_name_input.selectAll()  # Select any existing text for easy replacement
        
    def load_video(self):
        """Load an MP4 video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select MP4 Video", "", "Video Files (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.current_video_path = file_path
            media = self.instance.media_new(file_path)
            
            # Explicitly disable audio for this media
            media.add_option(':no-audio')
            
            self.media_player.set_media(media)
            
            # Ensure audio is muted at player level
            self.media_player.audio_set_mute(True)
            
            # Enable controls
            self.play_pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.start_button.setEnabled(True)
            self.frame_back_button.setEnabled(True)
            self.frame_forward_button.setEnabled(True)
            
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
        # Default to 30 fps (33.33ms per frame) if we can't determine the actual frame rate
        default_frame_duration = 1000 / 30  # ~33.33ms
        
        try:
            # Try to get video track information
            media = self.media_player.get_media()
            if media:
                # Parse media to get track info
                media.parse()
                tracks = media.tracks_get()
                for track in tracks:
                    if track.type == vlc.TrackType.video:
                        # Get frame rate from video track
                        fps = track.video.frame_rate_num / track.video.frame_rate_den if track.video.frame_rate_den > 0 else 30
                        return 1000 / fps
        except:
            pass
            
        return default_frame_duration
    
    def frame_forward(self):
        """Move one frame forward"""
        if self.media_player and self.current_video_path:
            # Pause the video first to ensure precise frame stepping
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            # Get current time and move forward to the next keyframe
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
            # Pause the video first to ensure precise frame stepping
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            # Get current time and move backward to the previous keyframe
            current_time = self.media_player.get_time()
            if current_time >= 0:
                frame_duration = self.get_frame_duration_ms()
                new_time = max(0, current_time - int(frame_duration))
                self.media_player.set_time(new_time)
                
    def frame_forward_10(self):
        """Move 10 frames forward"""
        if self.media_player and self.current_video_path:
            # Pause the video first to ensure precise frame stepping
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            # Get current time and move forward by 10 frame durations
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
            # Pause the video first to ensure precise frame stepping
            was_playing = self.media_player.is_playing()
            if was_playing:
                self.media_player.pause()
                self.play_pause_button.setText("▶️ Play")
            
            # Get current time and move backward by 10 frame durations
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
                
                # Update progress slider
                duration = self.media_player.get_length()
                if duration > 0:
                    position = int((current_time / duration) * 1000)
                    self.progress_slider.setValue(position)
                    
    def slider_pressed(self):
        """Handle slider press - pause updates"""
        self.timer.stop()
        
    def slider_released(self):
        """Handle slider release - seek and resume updates"""
        duration = self.media_player.get_length()
        if duration > 0:
            position = self.progress_slider.value() / 1000.0
            self.media_player.set_position(position)
        self.timer.start()
        
    def save_start_timestamp(self):
        """Save the current timestamp as start time"""
        if not self.current_video_path:
            return
            
        self.start_timestamp = self.get_current_timestamp_ms()
        if self.start_timestamp >= 0:
            formatted_time = self.format_timestamp(self.start_timestamp)
            self.start_time_label.setText(f"Start: {formatted_time}")
            self.end_button.setEnabled(True)
            
            # Update placeholder to suggest next segment name
            next_num = len(self.segments) + 1
            self.segment_name_input.setPlaceholderText(f"Segment {next_num} (or custom name)")
            
            # Update end button text to remind about naming
            self.end_button.setText("🔴 Save End & Name (E)")
            
            # Focus the input field for easy naming
            self.segment_name_input.setFocus()
        
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
                
            # Get title from input field or use default
            title = self.segment_name_input.text().strip()
            if not title:
                segment_num = len(self.segments) + 1
                title = f"Segment {segment_num}"
            
            segment = {
                'title': title,
                'start': self.start_timestamp,
                'end': end_timestamp
            }
            self.segments.append(segment)
            
            # Update display
            self.update_segments_display()
            
            # Reset for next segment
            self.start_timestamp = None
            self.start_time_label.setText("Start: Not set")
            self.end_button.setEnabled(False)
            self.end_button.setText("🔴 Save End (E)")  # Reset button text
            
            # Clear the input field for next segment
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
            display_text += f"{i:2d}. {segment['title']}\n"
            display_text += f"    {start_str} - {end_str}\n\n"
            
        # Temporarily disconnect signal to prevent infinite loop
        self.segments_display.textChanged.disconnect()
        self.segments_display.setText(display_text)
        self.segments_display.textChanged.connect(self.parse_segments_from_text)
        
    def parse_segments_from_text(self):
        """Parse segments from the text editor content"""
        text = self.segments_display.toPlainText()
        new_segments = []
        
        # Pattern to match lines like: "1. Title" followed by "    HH:MM:SS.mmm - HH:MM:SS.mmm"
        lines = text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^\s*\d+\.\s*', line):  # Line starts with number and dot
                # Extract title (everything after the number and dot)
                title_match = re.match(r'^\s*\d+\.\s*(.*)', line)
                if title_match:
                    title = title_match.group(1).strip()
                    
                    # Look for timestamp line
                    if i + 1 < len(lines):
                        timestamp_line = lines[i + 1].strip()
                        timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-\s*(\d{2}:\d{2}:\d{2}\.\d{3})', timestamp_line)
                        if timestamp_match:
                            start_str = timestamp_match.group(1)
                            end_str = timestamp_match.group(2)
                            
                            # Convert timestamps to milliseconds
                            try:
                                start_ms = self.timestamp_to_ms(start_str)
                                end_ms = self.timestamp_to_ms(end_str)
                                
                                if title and start_ms >= 0 and end_ms > start_ms:
                                    new_segments.append({
                                        'title': title,
                                        'start': start_ms,
                                        'end': end_ms
                                    })
                            except:
                                pass  # Skip invalid timestamps
                        i += 2  # Skip both title and timestamp line
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        # Update segments only if they changed
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
                self.start_time_label.setText("Start: Not set")
                self.end_button.setEnabled(False)
                self.update_segments_display()
                
    def export_timestamps(self):
        """Export timestamps to file"""
        if not self.segments:
            QMessageBox.warning(self, "Warning", "No segments to export!")
            return
        
        # Use simple "timestamps.txt" filename
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
                        f.write(f"{segment['title']};{start_str};{end_str}\n")
                        
                QMessageBox.information(
                    self, "Export Successful", 
                    f"Timestamps exported to:\n{file_path}\n\n{len(self.segments)} segments saved."
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export timestamps:\n{str(e)}")

    def closeEvent(self, event):
        """Handle application close event for cleanup."""
        if self.media_player:
            self.media_player.stop()
            self.media_player.release()
        if self.instance:
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
    del player  # Explicitly delete player to ensure cleanup
    sys.exit(exit_code)

if __name__ == "__main__":
    main()