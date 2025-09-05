# -*- coding: utf-8 -*-
"""
OpenCV Video Player Widget
"""

import os
import sys
from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal, QThread
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QSlider, QFileDialog, QMessageBox,
                                QToolBar, QAction, QStyle, QDialog)
from qgis.PyQt.QtGui import QImage, QPixmap
import numpy as np

# Try to import OpenCV
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

class VideoThread(QThread):
    """Thread for video playback"""
    frameReady = pyqtSignal(np.ndarray)
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.cap = None
        self.is_playing = False
        self.current_position = 0
        self.fps = 30
        self.frame_count = 0
        
    def load_video(self, file_path):
        """Load video file"""
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(file_path)
        if self.cap.isOpened():
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.durationChanged.emit(self.frame_count)
            return True
        return False
        
    def play(self):
        """Start playback"""
        self.is_playing = True
        
    def pause(self):
        """Pause playback"""
        self.is_playing = False
        
    def stop(self):
        """Stop playback"""
        self.is_playing = False
        self.current_position = 0
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
    def seek(self, position):
        """Seek to position"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            self.current_position = position
            # Emit a single frame when seeking
            ret, frame = self.cap.read()
            if ret:
                self.frameReady.emit(frame)
                self.positionChanged.emit(position)
                
    def run(self):
        """Thread main loop"""
        while self.cap:
            if self.is_playing and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.frameReady.emit(frame)
                    self.current_position = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    self.positionChanged.emit(self.current_position)
                    self.msleep(int(1000 / self.fps))  # Sleep based on FPS
                else:
                    # End of video
                    self.is_playing = False
                    self.stop()
            else:
                self.msleep(30)  # Sleep when not playing

class OpenCVVideoPlayer(QWidget):
    """Video player widget using OpenCV"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_thread = VideoThread()
        self.current_video_path = None
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Play/Pause action
        self.play_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaPlay),
            self.tr("Play"), self
        )
        self.play_action.triggered.connect(self.play_pause)
        self.play_action.setEnabled(False)
        toolbar.addAction(self.play_action)
        
        # Stop action
        self.stop_action = QAction(
            self.style().standardIcon(QStyle.SP_MediaStop),
            self.tr("Stop"), self
        )
        self.stop_action.triggered.connect(self.stop)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)
        
        toolbar.addSeparator()
        
        # External player action
        external_action = QAction(self.tr("Open in External Player"), self)
        external_action.triggered.connect(self.open_external)
        toolbar.addAction(external_action)
        
        layout.addWidget(toolbar)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid #ccc;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setScaledContents(True)
        layout.addWidget(self.video_label, 1)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.time_label)
        
        # Position slider
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setEnabled(False)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.position_slider.sliderPressed.connect(self.slider_pressed)
        self.position_slider.sliderReleased.connect(self.slider_released)
        controls_layout.addWidget(self.position_slider, 1)
        
        layout.addLayout(controls_layout)
        
        # Info label
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        
        # State
        self.is_seeking = False
        
    def setup_connections(self):
        """Setup signal connections"""
        self.video_thread.frameReady.connect(self.update_frame)
        self.video_thread.positionChanged.connect(self.update_position)
        self.video_thread.durationChanged.connect(self.update_duration)
        
    def load_video_file(self, file_path):
        """Load a specific video file"""
        if not OPENCV_AVAILABLE:
            QMessageBox.warning(self, self.tr("OpenCV Not Available"), 
                              self.tr("OpenCV is required for video playback.\nInstall with: pip install opencv-python"))
            self.open_external_player(file_path)
            return
            
        self.current_video_path = file_path
        
        # Update info
        file_info = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        self.info_label.setText(f"Video: {file_info} ({file_size:.1f} MB)")
        
        # Load video in thread
        if self.video_thread.load_video(file_path):
            self.play_action.setEnabled(True)
            self.stop_action.setEnabled(True)
            self.position_slider.setEnabled(True)
            
            # Start thread if not running
            if not self.video_thread.isRunning():
                self.video_thread.start()
                
            # Get first frame
            self.video_thread.seek(0)
        else:
            QMessageBox.warning(self, self.tr("Error"), 
                              self.tr("Could not load video file"))
            
    def play_pause(self):
        """Toggle play/pause"""
        if self.video_thread.is_playing:
            self.video_thread.pause()
            self.play_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_action.setText(self.tr("Play"))
        else:
            self.video_thread.play()
            self.play_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.play_action.setText(self.tr("Pause"))
            
    def stop(self):
        """Stop playback"""
        self.video_thread.stop()
        self.play_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_action.setText(self.tr("Play"))
        
    def slider_pressed(self):
        """Handle slider press"""
        self.is_seeking = True
        
    def slider_released(self):
        """Handle slider release"""
        self.is_seeking = False
        
    def set_position(self, position):
        """Set playback position"""
        self.video_thread.seek(position)
        
    def update_frame(self, frame):
        """Update displayed frame"""
        # Convert frame to QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create QImage
        q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)
        
    def update_position(self, position):
        """Update position slider and time label"""
        if not self.is_seeking:
            self.position_slider.setValue(position)
            
        # Update time label
        if self.video_thread.fps > 0:
            current_time = position / self.video_thread.fps
            total_time = self.video_thread.frame_count / self.video_thread.fps
            
            current_str = self.format_time(current_time)
            total_str = self.format_time(total_time)
            self.time_label.setText(f"{current_str} / {total_str}")
            
    def update_duration(self, duration):
        """Update duration"""
        self.position_slider.setRange(0, duration)
        
    def format_time(self, seconds):
        """Format time as MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def open_external(self):
        """Open in external player"""
        if self.current_video_path:
            self.open_external_player(self.current_video_path)
            
    def open_external_player(self, file_path):
        """Open file with default application"""
        import subprocess
        import platform
        
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', file_path])
        elif platform.system() == 'Windows':
            os.startfile(file_path)
        else:  # Linux
            subprocess.call(['xdg-open', file_path])
            
    def closeEvent(self, event):
        """Handle close event"""
        # Stop thread
        self.video_thread.is_playing = False
        if self.video_thread.cap:
            self.video_thread.cap.release()
        self.video_thread.quit()
        self.video_thread.wait()
        event.accept()
        
    def tr(self, text):
        """Translate text"""
        return text