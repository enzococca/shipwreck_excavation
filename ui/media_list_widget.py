# -*- coding: utf-8 -*-
"""
Simple media list widget for displaying associated media in dialogs
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QListWidget, QListWidgetItem, QLabel, QGroupBox,
                                QMessageBox)
from qgis.PyQt.QtGui import QIcon, QPixmap
import os

class MediaListWidget(QWidget):
    """Widget to display media items associated with an entity"""
    
    def __init__(self, db_manager, item_type, item_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.item_type = item_type  # 'site', 'find', 'dive'
        self.item_id = item_id
        
        self.init_ui()
        
        if item_id:
            self.load_media()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.media_label = QLabel(self.tr("Associated Media:"))
        header_layout.addWidget(self.media_label)
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton(self.tr("Refresh"))
        self.refresh_btn.clicked.connect(self.load_media)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Media list
        self.media_list = QListWidget()
        self.media_list.setMaximumHeight(150)
        layout.addWidget(self.media_list)
        
        # Count label
        self.count_label = QLabel(self.tr("No media attached"))
        layout.addWidget(self.count_label)
        
        self.setLayout(layout)
    
    def set_item(self, item_type, item_id):
        """Set or update the item to display media for"""
        self.item_type = item_type
        self.item_id = item_id
        self.load_media()
    
    def load_media(self):
        """Load media for the current item"""
        self.media_list.clear()
        
        if not self.item_id:
            self.count_label.setText(self.tr("No media attached"))
            return
        
        try:
            # Get media for item
            media_items = self.db_manager.get_media_for_item(self.item_type, self.item_id)
            
            if not media_items:
                self.count_label.setText(self.tr("No media attached"))
                return
            
            # Add items to list
            for media in media_items:
                QgsMessageLog.logMessage(f"Processing media: {media}", "MediaListWidget", Qgis.Info)
                # Create list item
                item_text = f"{media.get('media_type', 'Unknown')} - {media.get('file_name', 'Unknown')}"
                
                if media.get('description'):
                    item_text += f"\n{media['description']}"
                
                if media.get('capture_date'):
                    item_text += f"\n{media['capture_date']}"
                    
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, media)
                
                # Set icon based on type
                media_type = media.get('media_type', '').lower()
                if media_type == 'photo':
                    # Try to load thumbnail
                    file_path = media.get('file_path')
                    if file_path:
                        pixmap = None
                        
                        # Check if it's an absolute path
                        if os.path.isabs(file_path) and os.path.exists(file_path):
                            pixmap = QPixmap(file_path)
                        else:
                            # It's a relative path
                            if os.path.exists(file_path):
                                pixmap = QPixmap(file_path)
                            else:
                                # Try with configured media base path
                                media_base = self.db_manager.get_setting('media_base_path')
                                QgsMessageLog.logMessage(f"Retrieved media_base_path: {media_base}", "MediaListWidget", Qgis.Info)
                                if media_base:
                                    # Remove 'media' from the base path if it's already included
                                    if media_base.endswith('/media') or media_base.endswith('\\media'):
                                        base_path = os.path.dirname(media_base)
                                    else:
                                        base_path = media_base
                                    
                                    # Normalize the path for the current OS
                                    # Replace forward slashes with OS-specific separator
                                    normalized_file_path = file_path.replace('/', os.sep).replace('\\', os.sep)
                                    full_drive_path = os.path.join(base_path, normalized_file_path)
                                    QgsMessageLog.logMessage(f"base_path={base_path}", "MediaListWidget", Qgis.Info)
                                    QgsMessageLog.logMessage(f"file_path={file_path}", "MediaListWidget", Qgis.Info)
                                    QgsMessageLog.logMessage(f"normalized_file_path={normalized_file_path}", "MediaListWidget", Qgis.Info)
                                    QgsMessageLog.logMessage(f"full_drive_path={full_drive_path}", "MediaListWidget", Qgis.Info)
                                    QgsMessageLog.logMessage(f"exists={os.path.exists(full_drive_path)}", "MediaListWidget", Qgis.Info)
                                else:
                                    # No configured path, try relative to current directory
                                    full_drive_path = file_path
                                if os.path.exists(full_drive_path):
                                    pixmap = QPixmap(full_drive_path)
                        
                        if pixmap and not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            item.setIcon(QIcon(scaled_pixmap))
                        else:
                            item.setIcon(QIcon.fromTheme('image'))
                    else:
                        item.setIcon(QIcon.fromTheme('image'))
                elif media_type == 'video':
                    item.setIcon(QIcon.fromTheme('video'))
                elif media_type == '3d':
                    item.setIcon(QIcon.fromTheme('view-3d'))
                else:
                    item.setIcon(QIcon.fromTheme('document'))
                
                self.media_list.addItem(item)
            
            # Update count
            count = len(media_items)
            self.count_label.setText(self.tr(f"{count} media file{'s' if count != 1 else ''} attached"))
            
        except Exception as e:
            QMessageBox.warning(self, self.tr("Error"), 
                              self.tr(f"Error loading media: {str(e)}"))
    
    def get_media_count(self):
        """Get the number of media items"""
        return self.media_list.count()