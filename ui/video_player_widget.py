# -*- coding: utf-8 -*-
"""
Video Player Widget
"""

import os
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal, QTimer
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QSlider, QFileDialog, QMessageBox,
                                QToolBar, QAction, QStyle)
from qgis.PyQt.QtGui import QIcon, QPixmap

# Try to import multimedia support
try:
    from qgis.PyQt.QtMultimedia import QMediaPlayer, QMediaContent
    from qgis.PyQt.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
    print("Qt Multimedia is available")
except ImportError as e:
    MULTIMEDIA_AVAILABLE = False
    print(f"Qt Multimedia not available: {e}")

# Fallback to external player
import subprocess
import platform


class VideoPlayerWidget(QWidget):
    """Widget for playing video files"""
    
    video_loaded = pyqtSignal(str)  # Emitted when a video is loaded
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_video_path = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Load video action
        load_action = QAction(QIcon(), self.tr("Load Video"), self)
        load_action.triggered.connect(self.load_video)
        toolbar.addAction(load_action)
        
        toolbar.addSeparator()
        
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
        
        # Screenshot action
        screenshot_action = QAction(QIcon(), self.tr("Screenshot"), self)
        screenshot_action.triggered.connect(self.take_screenshot)
        toolbar.addAction(screenshot_action)
        
        # External player action
        external_action = QAction(QIcon(), self.tr("Open in External Player"), self)
        external_action.triggered.connect(self.open_external)
        toolbar.addAction(external_action)
        
        layout.addWidget(toolbar)
        
        # Video widget
        if MULTIMEDIA_AVAILABLE:
            self.setup_qt_player()
            layout.addWidget(self.video_widget, 1)
        else:
            # Fallback UI
            self.preview_label = QLabel(self.tr("Video player not available.\nClick 'Open in External Player' to view videos."))
            self.preview_label.setAlignment(Qt.AlignCenter)
            self.preview_label.setStyleSheet("background-color: #000; color: #fff; border: 1px solid #ccc;")
            self.preview_label.setMinimumHeight(300)
            layout.addWidget(self.preview_label, 1)
            
        # Controls
        controls_layout = QHBoxLayout()
        
        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        controls_layout.addWidget(self.time_label)
        
        # Position slider
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setEnabled(False)
        if MULTIMEDIA_AVAILABLE:
            self.position_slider.sliderMoved.connect(self.set_position)
        controls_layout.addWidget(self.position_slider, 1)
        
        # Volume control
        controls_layout.addWidget(QLabel(self.tr("Volume:")))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(100)
        if MULTIMEDIA_AVAILABLE:
            self.volume_slider.valueChanged.connect(self.set_volume)
        controls_layout.addWidget(self.volume_slider)
        
        layout.addLayout(controls_layout)
        
        # Info panel
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        
        # Timer for updating position
        if MULTIMEDIA_AVAILABLE:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_position)
            self.timer.start(100)
            
    def setup_qt_player(self):
        """Setup Qt multimedia player"""
        if not MULTIMEDIA_AVAILABLE:
            return
            
        # Create media player
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        
        # Create video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(300)
        
        # Set video output
        self.media_player.setVideoOutput(self.video_widget)
        
        # Connect signals
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.error.connect(self.handle_error)
        
    def load_video_file(self, file_path):
        """Load a specific video file"""
        self.load_video(file_path)
        
        # Auto-play if multimedia is available
        if MULTIMEDIA_AVAILABLE and self.media_player:
            # Give it a moment to load
            QTimer.singleShot(500, self.media_player.play)
    
    def load_video(self, file_path=None):
        """Load video file"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Load Video"),
                "",
                "Video Files (*.mp4 *.avi *.mov *.wmv *.mkv);;All Files (*.*)"
            )
            
        if not file_path:
            return
            
        self.current_video_path = file_path
        
        # Update info
        file_info = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        self.info_label.setText(
            self.tr(f"Video: {file_info}\nSize: {file_size:.2f} MB")
        )
        
        if MULTIMEDIA_AVAILABLE:
            # Load in Qt player
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            self.play_action.setEnabled(True)
            self.stop_action.setEnabled(True)
            self.position_slider.setEnabled(True)
            
            # Check if Qt Multimedia is properly initialized
            from qgis.PyQt.QtMultimedia import QMediaPlayer
            
            # Update UI to show status
            supported_formats = ['mp4', 'avi', 'mov', 'wmv', 'webm']
            file_ext = os.path.splitext(file_path)[1].lower()[1:]
            
            if file_ext not in supported_formats:
                self.info_label.setText(
                    self.tr(f"Video loaded. Format '{file_ext}' may not be supported.\n"
                          f"Supported formats: {', '.join(supported_formats)}\n"
                          f"Try 'Open in External Player' if playback fails.")
                )
            else:
                self.info_label.setText(
                    self.tr(f"Video loaded. Click Play to start.\n"
                          f"If playback doesn't work, try 'Open in External Player'.")
                )
        else:
            # Show preview frame if possible
            self.extract_preview_frame(file_path)
            
        self.video_loaded.emit(file_path)
        
    def extract_preview_frame(self, video_path):
        """Extract a preview frame from video using ffmpeg"""
        try:
            import tempfile
            
            # Create temp file for frame
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Extract frame at 1 second
            cmd = [
                'ffmpeg',
                '-ss', '00:00:01',
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                temp_path
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=5)
            
            if os.path.exists(temp_path):
                pixmap = QPixmap(temp_path)
                self.preview_label.setPixmap(
                    pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                os.unlink(temp_path)
        except:
            # ffmpeg not available or error
            pass
            
    def play_pause(self):
        """Toggle play/pause"""
        if not MULTIMEDIA_AVAILABLE:
            return
            
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
            
    def stop(self):
        """Stop playback"""
        if not MULTIMEDIA_AVAILABLE:
            return
            
        self.media_player.stop()
        
    def set_position(self, position):
        """Set playback position"""
        if not MULTIMEDIA_AVAILABLE:
            return
            
        self.media_player.setPosition(position)
        
    def set_volume(self, volume):
        """Set volume"""
        if not MULTIMEDIA_AVAILABLE:
            return
            
        self.media_player.setVolume(volume)
        
    def media_state_changed(self, state):
        """Handle media state changes"""
        if state == QMediaPlayer.PlayingState:
            self.play_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.play_action.setText(self.tr("Pause"))
        else:
            self.play_action.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.play_action.setText(self.tr("Play"))
            
    def position_changed(self, position):
        """Handle position changes"""
        self.position_slider.setValue(position)
        
    def duration_changed(self, duration):
        """Handle duration changes"""
        self.position_slider.setRange(0, duration)
        
    def update_position(self):
        """Update position display"""
        if not MULTIMEDIA_AVAILABLE or not hasattr(self, 'media_player'):
            return
            
        position = self.media_player.position()
        duration = self.media_player.duration()
        
        if duration > 0:
            position_time = self.format_time(position)
            duration_time = self.format_time(duration)
            self.time_label.setText(f"{position_time} / {duration_time}")
            
    def format_time(self, milliseconds):
        """Format time from milliseconds"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
        
    def handle_error(self):
        """Handle media player errors"""
        if MULTIMEDIA_AVAILABLE:
            error = self.media_player.errorString()
            QMessageBox.warning(
                self,
                self.tr("Playback Error"),
                self.tr(f"Error playing video: {error}\n\n"
                      f"Try using 'Open in External Player' if the format is not supported.\n"
                      f"Qt Multimedia may have limited codec support on some systems.")
            )
            
            # Suggest opening in external player
            self.open_external()
            
    def take_screenshot(self):
        """Take screenshot of current frame"""
        if not self.current_video_path:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Screenshot"),
            "screenshot.png",
            "PNG Files (*.png);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'video_widget'):
            # Grab frame from video widget
            pixmap = self.video_widget.grab()
            pixmap.save(file_path)
            
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr("Screenshot saved successfully")
            )
        else:
            # Try to extract frame using ffmpeg
            position = "00:00:01"  # Default to 1 second
            cmd = [
                'ffmpeg',
                '-ss', position,
                '-i', self.current_video_path,
                '-vframes', '1',
                '-q:v', '2',
                file_path
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
                if os.path.exists(file_path):
                    QMessageBox.information(
                        self,
                        self.tr("Success"),
                        self.tr("Screenshot saved successfully")
                    )
            except:
                QMessageBox.warning(
                    self,
                    self.tr("Error"),
                    self.tr("Failed to save screenshot")
                )
                
    def open_external(self):
        """Open video in external player"""
        if not self.current_video_path:
            return
            
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', self.current_video_path])
            elif platform.system() == 'Windows':
                os.startfile(self.current_video_path)
            else:  # Linux
                subprocess.call(['xdg-open', self.current_video_path])
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr(f"Failed to open video: {str(e)}")
            )
            
    def tr(self, message):
        """Translate message"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('VideoPlayerWidget', message)