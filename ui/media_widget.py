# -*- coding: utf-8 -*-
"""Media management widget with drag-and-drop support"""

import os
import shutil
from datetime import datetime
from qgis.PyQt.QtCore import Qt, QMimeData, pyqtSignal, QSize
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QListWidget, QListWidgetItem, QComboBox,
                                QPushButton, QTableWidget, QTableWidgetItem,
                                QHeaderView, QMessageBox, QFileDialog,
                                QMenu, QToolBar, QSplitter, QGroupBox,
                                QApplication, QDialog)
from qgis.PyQt.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon
from qgis.core import QgsProject, QgsMessageLog, Qgis

import sys
from pathlib import Path
plugin_dir = Path(__file__).parent.parent
if str(plugin_dir) not in sys.path:
    sys.path.insert(0, str(plugin_dir))

from utils.media_path_manager import MediaPathManager

class MediaDropWidget(QListWidget):
    """Custom widget to handle drag and drop"""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setAlternatingRowColors(True)
        self.setIconSize(QSize(64, 64))
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event):
        """Handle drag move event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    files.append(file_path)
            
            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
        else:
            event.ignore()

class MediaWidget(QWidget):
    """Media management widget"""
    
    def __init__(self, iface, db_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.db_manager = db_manager
        self.current_site_id = None
        self.media_folder = None
        
        # Initialize media path manager with db_manager for settings access
        self.media_path_manager = MediaPathManager(db_manager.db_path, db_manager)
        
        # Get or create media folder
        self.setup_media_folder()
        self.init_ui()
        self.load_sites()
        
    def setup_media_folder(self):
        """Setup media storage folder"""
        # Try to get configured media path from settings
        configured_path = self.db_manager.get_setting('media_base_path')
        if configured_path and os.path.exists(configured_path):
            # Check if the path already includes 'media' folder
            if configured_path.endswith('/media') or configured_path.endswith('\\media'):
                self.media_folder = configured_path
            else:
                self.media_folder = os.path.join(configured_path, "media")
        else:
            # Get project folder as fallback
            project_path = QgsProject.instance().absolutePath()
            if project_path:
                self.media_folder = os.path.join(project_path, "media")
            else:
                # Use database folder
                db_path = self.db_manager.db_path
                if db_path:
                    self.media_folder = os.path.join(os.path.dirname(db_path), "media")
                else:
                    self.media_folder = os.path.expanduser("~/Documents/ShipwreckMedia")
        
        # Create folder if it doesn't exist
        if not os.path.exists(self.media_folder):
            os.makedirs(self.media_folder)
            
        # Create subfolders
        for folder in ['photos', 'videos', 'documents', 'thumbnails']:
            subfolder = os.path.join(self.media_folder, folder)
            if not os.path.exists(subfolder):
                os.makedirs(subfolder)
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Site selector
        toolbar.addWidget(QLabel(self.tr("Site:")))
        self.site_combo = QComboBox()
        self.site_combo.setMinimumWidth(200)
        self.site_combo.currentIndexChanged.connect(self.on_site_changed)
        toolbar.addWidget(self.site_combo)
        
        toolbar.addSeparator()
        
        # Filter by type
        toolbar.addWidget(QLabel(self.tr("Type:")))
        self.type_combo = QComboBox()
        self.type_combo.addItems([self.tr("All"), "Photo", "Video", "Document"])
        self.type_combo.currentTextChanged.connect(self.filter_media)
        toolbar.addWidget(self.type_combo)
        
        # Filter by association
        toolbar.addWidget(QLabel(self.tr("Associated with:")))
        self.assoc_combo = QComboBox()
        self.assoc_combo.addItems([self.tr("All"), "Site", "Find", "Dive"])
        self.assoc_combo.currentTextChanged.connect(self.filter_media)
        toolbar.addWidget(self.assoc_combo)
        
        toolbar.addSeparator()
        
        # Actions
        self.delete_action = toolbar.addAction(self.tr("Delete"))
        self.delete_action.triggered.connect(self.delete_media)
        self.delete_action.setEnabled(False)
        
        self.export_action = toolbar.addAction(self.tr("Export List"))
        self.export_action.triggered.connect(self.export_media_list)
        
        layout.addWidget(toolbar)
        
        # Main area - splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - drop area
        drop_group = QGroupBox(self.tr("Drag && Drop Media Files"))
        drop_layout = QVBoxLayout()
        
        self.drop_widget = MediaDropWidget()
        self.drop_widget.files_dropped.connect(self.handle_dropped_files)
        drop_layout.addWidget(self.drop_widget)
        
        # Association controls
        assoc_layout = QHBoxLayout()
        assoc_layout.addWidget(QLabel(self.tr("Associate with:")))
        
        self.assoc_type_combo = QComboBox()
        self.assoc_type_combo.addItems(["Site", "Find", "Dive"])
        self.assoc_type_combo.currentTextChanged.connect(self.on_assoc_type_changed)
        assoc_layout.addWidget(self.assoc_type_combo)
        
        # Set default to Site
        self.assoc_type_combo.setCurrentIndex(0)
        
        self.assoc_id_combo = QComboBox()
        assoc_layout.addWidget(self.assoc_id_combo)
        
        # Load associations will be called when site is selected
        
        drop_layout.addLayout(assoc_layout)
        drop_group.setLayout(drop_layout)
        
        splitter.addWidget(drop_group)
        
        # Right side - media list
        media_group = QGroupBox(self.tr("Media Files"))
        media_layout = QVBoxLayout()
        
        self.media_table = QTableWidget()
        self.media_table.setColumnCount(7)
        self.media_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Preview"), self.tr("Filename"), self.tr("Type"),
            self.tr("Associated"), self.tr("Date"), self.tr("Size")
        ])
        # Set preview column width
        self.media_table.setColumnWidth(1, 80)
        self.media_table.horizontalHeader().setStretchLastSection(True)
        self.media_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.media_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.media_table.itemDoubleClicked.connect(self.view_media)
        # Hide ID column
        self.media_table.hideColumn(0)
        # Set row height for thumbnails
        self.media_table.verticalHeader().setDefaultSectionSize(60)
        
        media_layout.addWidget(self.media_table)
        media_group.setLayout(media_layout)
        
        splitter.addWidget(media_group)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        # Status
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def load_sites(self):
        """Load sites into combo box"""
        self.site_combo.clear()
        self.site_combo.addItem(self.tr("Select Site..."), None)
        
        sites = self.db_manager.execute_query("SELECT id, site_name FROM sites WHERE status = 'active' ORDER BY site_name")
        if sites:
            for site in sites:
                if isinstance(site, dict):
                    self.site_combo.addItem(site['site_name'], site['id'])
                else:
                    self.site_combo.addItem(site[1], site[0])
                    
    def refresh_data(self):
        """Refresh data when tab is activated"""
        self.load_sites()
        if self.current_site_id:
            # Restore site selection
            for i in range(self.site_combo.count()):
                if self.site_combo.itemData(i) == self.current_site_id:
                    self.site_combo.setCurrentIndex(i)
                    break
    
    def on_site_changed(self, index):
        """Handle site selection change"""
        self.current_site_id = self.site_combo.currentData()
        self.refresh_data()
        self.load_associations()
        
        # Debug
        QgsMessageLog.logMessage(f"Site changed - ID: {self.current_site_id}", "Shipwreck", level=0)
    
    def on_assoc_type_changed(self, assoc_type):
        """Handle association type change"""
        self.load_associations()
    
    def load_associations(self):
        """Load items for association"""
        self.assoc_id_combo.clear()
        
        if not self.current_site_id:
            QgsMessageLog.logMessage("No site selected for associations", "Shipwreck", level=1)
            return
            
        assoc_type = self.assoc_type_combo.currentText()
        QgsMessageLog.logMessage(f"Loading associations - Type: {assoc_type}, Site: {self.current_site_id}", "Shipwreck", level=0)
        
        if assoc_type == "Site":
            self.assoc_id_combo.addItem(self.site_combo.currentText(), self.current_site_id)
        
        elif assoc_type == "Find":
            finds = self.db_manager.execute_query(
                "SELECT id, find_number FROM finds WHERE site_id = ? ORDER BY find_number",
                (self.current_site_id,)
            )
            if finds:
                for find in finds:
                    if isinstance(find, dict):
                        self.assoc_id_combo.addItem(find['find_number'], find['id'])
                    else:
                        self.assoc_id_combo.addItem(find[1], find[0])
        
        elif assoc_type == "Dive":
            dives = self.db_manager.execute_query(
                "SELECT id, dive_number FROM dive_logs WHERE site_id = ? ORDER BY dive_number",
                (self.current_site_id,)
            )
            if dives:
                for dive in dives:
                    if isinstance(dive, dict):
                        self.assoc_id_combo.addItem(dive['dive_number'], dive['id'])
                    else:
                        self.assoc_id_combo.addItem(dive[1], dive[0])
    
    def handle_dropped_files(self, files):
        """Handle dropped files"""
        if not self.current_site_id:
            QMessageBox.warning(
                self,
                self.tr("No Site Selected"),
                self.tr("Please select a site before adding media files")
            )
            return
        
        # Get association
        assoc_type = self.assoc_type_combo.currentText().lower()
        assoc_id = self.assoc_id_combo.currentData()
        
        if not assoc_id:
            QMessageBox.warning(
                self,
                self.tr("No Association"),
                self.tr("Please select what to associate the media with")
            )
            return
        
        added = 0
        for file_path in files:
            if self.add_media_file(file_path, assoc_type, assoc_id):
                added += 1
        
        if added > 0:
            self.refresh_data()
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr(f"Added {added} media file(s)")
            )
    
    def add_media_file(self, file_path, related_type, related_id):
        """Add a media file to the database"""
        try:
            # Get file info
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Skip only MTL files (they're copied with OBJ files)
            # Don't skip texture files as they might be standalone photos
            if file_ext in ['.mtl']:
                return True  # Return True to not show error, but don't add to database
            
            # Determine media type
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif']:
                media_type = 'photo'
                subfolder = 'photos'
            elif file_ext in ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.webm', '.flv']:
                media_type = 'video'
                subfolder = 'videos'
            elif file_ext in ['.obj', '.stl', '.ply', '.dae', '.fbx', '.3ds']:
                media_type = '3d_model'
                subfolder = '3d_models'
            elif file_ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt']:
                media_type = 'document'
                subfolder = 'documents'
            else:
                media_type = 'other'
                subfolder = 'other'
            
            # Import file using media path manager for relative paths
            relative_path = self.media_path_manager.import_media_file(file_path, media_type, copy=True)
            
            if not relative_path:
                QMessageBox.warning(self, "Error", f"Failed to import {filename}")
                return False
            
            # Get absolute path for further processing
            dest_path = self.media_path_manager.get_absolute_path(relative_path)
            
            # For OBJ files, also copy associated MTL and texture files
            if file_ext == '.obj':
                self.copy_obj_dependencies(file_path, dest_path)
            
            # Create thumbnail
            if media_type == 'photo':
                self.create_thumbnail(dest_path)
            elif media_type == 'video':
                self.create_video_thumbnail(dest_path)
            elif media_type == '3d_model':
                self.create_3d_thumbnail(dest_path)
            
            # Add to database with relative path
            media_data = {
                'media_type': media_type,
                'file_name': os.path.basename(dest_path),
                'file_path': relative_path,  # Store relative path in database
                'file_size': file_size,
                'description': f"Imported from {filename}",
                'capture_date': datetime.now().isoformat()  # Convert to ISO string for JSON serialization
            }
            
            media_id = self.db_manager.add_media(media_data, related_type, related_id)
            
            if media_id:
                QgsMessageLog.logMessage(f"Media added successfully with ID: {media_id}", 
                                       "MediaWidget", Qgis.Info)
                
                # Add to drop widget
                item = QListWidgetItem(filename)
                
                # Try to set thumbnail for any media type
                thumb_path = self.get_thumbnail_path(dest_path)
                if thumb_path and os.path.exists(thumb_path):
                    pixmap = QPixmap(thumb_path)
                    if not pixmap.isNull():
                        item.setIcon(QIcon(pixmap))
                
                # Refresh the media list to show the new item
                self.refresh_data()
            else:
                QgsMessageLog.logMessage(f"Failed to add media to database", 
                                       "MediaWidget", Qgis.Critical)
                
            # Set default icon based on type for all items
            if not item.icon().isNull():
                pass  # Icon already set from thumbnail
            elif media_type == 'video':
                item.setText(f"🎬 {filename}")
            elif media_type == '3d_model':
                item.setText(f"🎲 {filename}")
            elif media_type == 'document':
                item.setText(f"📄 {filename}")
            
            self.drop_widget.addItem(item)
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error adding media: {str(e)}", "Shipwreck", level=2)
            return False
    
    def copy_obj_dependencies(self, obj_path, dest_obj_path):
        """Copy MTL and texture files associated with OBJ file"""
        try:
            obj_dir = os.path.dirname(obj_path)
            dest_dir = os.path.dirname(dest_obj_path)
            
            # Look for MTL file
            obj_name = os.path.splitext(os.path.basename(obj_path))[0]
            mtl_path = os.path.join(obj_dir, f"{obj_name}.mtl")
            
            if os.path.exists(mtl_path):
                dest_mtl = os.path.join(dest_dir, os.path.basename(mtl_path))
                shutil.copy2(mtl_path, dest_mtl)
                
                # Parse MTL file for texture references
                with open(mtl_path, 'r') as f:
                    mtl_content = f.read()
                
                # Find texture file references in MTL
                import re
                texture_patterns = [
                    r'map_Kd\s+(.+)',  # Diffuse texture
                    r'map_Ks\s+(.+)',  # Specular texture
                    r'map_Ka\s+(.+)',  # Ambient texture
                    r'map_Bump\s+(.+)',  # Bump map
                    r'map_d\s+(.+)',  # Alpha texture
                    r'norm\s+(.+)'  # Normal map
                ]
                
                textures = set()
                for pattern in texture_patterns:
                    matches = re.findall(pattern, mtl_content)
                    textures.update(matches)
                
                # Copy texture files
                for texture in textures:
                    texture = texture.strip()
                    texture_path = os.path.join(obj_dir, texture)
                    if os.path.exists(texture_path):
                        dest_texture = os.path.join(dest_dir, os.path.basename(texture))
                        shutil.copy2(texture_path, dest_texture)
                        
        except Exception as e:
            QgsMessageLog.logMessage(f"Error copying OBJ dependencies: {str(e)}", "Shipwreck", level=1)
    
    def create_video_thumbnail(self, video_path):
        """Create thumbnail for video file"""
        try:
            # Try using opencv first
            try:
                import cv2
                cap = cv2.VideoCapture(video_path)
                ret, frame = cap.read()
                if ret:
                    # Get a frame from 1 second into the video
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(fps))
                    ret, frame = cap.read()
                    
                    if ret:
                        thumb_dir = os.path.join(os.path.dirname(video_path), '..', 'thumbnails')
                        os.makedirs(thumb_dir, exist_ok=True)
                        
                        thumb_name = f"thumb_{os.path.basename(video_path)}.jpg"
                        thumb_path = os.path.join(thumb_dir, thumb_name)
                        
                        # Resize frame
                        height, width = frame.shape[:2]
                        if width > 150:
                            scale = 150 / width
                            new_width = 150
                            new_height = int(height * scale)
                            frame = cv2.resize(frame, (new_width, new_height))
                        
                        cv2.imwrite(thumb_path, frame)
                cap.release()
                return
            except ImportError:
                pass
            
            # Fallback: create a generic video thumbnail
            self.create_generic_thumbnail(video_path, 'video')
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating video thumbnail: {str(e)}", "Shipwreck", level=1)
            self.create_generic_thumbnail(video_path, 'video')
    
    def create_3d_thumbnail(self, model_path):
        """Create thumbnail for 3D model file"""
        try:
            # For now, create a generic 3D model thumbnail
            # In the future, we could render the model to an image
            self.create_generic_thumbnail(model_path, '3d')
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating 3D thumbnail: {str(e)}", "Shipwreck", level=1)
    
    def create_generic_thumbnail(self, file_path, file_type):
        """Create a generic thumbnail with file type icon"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create thumbnail directory
            thumb_dir = os.path.join(os.path.dirname(file_path), '..', 'thumbnails')
            os.makedirs(thumb_dir, exist_ok=True)
            
            thumb_name = f"thumb_{os.path.basename(file_path)}.jpg"
            thumb_path = os.path.join(thumb_dir, thumb_name)
            
            # Create image with icon
            img = Image.new('RGB', (150, 150), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw file type text
            text = {'video': '🎬', '3d': '🎲'}.get(file_type, '📄')
            
            try:
                # Try to use a font
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
            except:
                font = None
            
            # Get text size and center it
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = 60
                text_height = 60
            
            x = (150 - text_width) // 2
            y = (150 - text_height) // 2
            
            draw.text((x, y), text, fill='black', font=font)
            
            # Add file extension
            ext = os.path.splitext(file_path)[1].upper()
            draw.text((75, 120), ext, fill='gray', anchor='mm')
            
            img.save(thumb_path, 'JPEG')
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating generic thumbnail: {str(e)}", "Shipwreck", level=1)
    
    def create_thumbnail(self, image_path):
        """Create thumbnail for image"""
        try:
            from PIL import Image
            
            thumb_path = self.get_thumbnail_path(image_path)
            
            with Image.open(image_path) as img:
                img.thumbnail((150, 150))
                img.save(thumb_path)
                
        except ImportError:
            # PIL not available
            pass
        except Exception as e:
            QgsMessageLog.logMessage(f"Error creating thumbnail: {str(e)}", "Shipwreck", level=1)
    
    def get_thumbnail_path(self, image_path):
        """Get thumbnail path for image"""
        if not image_path:
            return None
        filename = os.path.basename(image_path)
        return os.path.join(self.media_folder, 'thumbnails', f"thumb_{filename}")
    
    def refresh_data(self):
        """Refresh media list"""
        if not self.current_site_id:
            self.media_table.setRowCount(0)
            return
        
        # Get media for current site
        # Check if database manager has the get_media_for_site method
        if hasattr(self.db_manager, 'get_media_for_site'):
            media_files = self.db_manager.get_media_for_site(self.current_site_id)
            print(f"DEBUG: Got {len(media_files) if media_files else 0} media files for site {self.current_site_id}")
            if media_files and len(media_files) > 0:
                print(f"DEBUG: First media file: {media_files[0]}")
        else:
            # Fallback to complex query for SQLite
            query = """
                SELECT m.*, mr.related_type, mr.related_id
                FROM media m
                JOIN media_relations mr ON m.id = mr.media_id
                WHERE mr.related_id IN (
                    SELECT id FROM sites WHERE id = ?
                    UNION
                    SELECT id FROM finds WHERE site_id = ?
                    UNION  
                    SELECT id FROM dive_logs WHERE site_id = ?
                )
                ORDER BY m.created_at DESC
            """
            media_files = self.db_manager.execute_query(query, (self.current_site_id, self.current_site_id, self.current_site_id))
        
        self.media_table.setRowCount(0)
        
        if media_files:
            for media in media_files:
                row = self.media_table.rowCount()
                self.media_table.insertRow(row)
                
                # Extract values
                if isinstance(media, dict):
                    media_id = str(media['id'])
                    # Try different possible column names
                    filename = media.get('file_name') or media.get('filename') or media.get('name', 'Unknown')
                    media_type = media.get('media_type', 'photo')
                    related_type = media.get('related_type', '')
                    file_size = media.get('file_size', 0)
                    created_at = media.get('created_at', '')
                    file_path = media.get('file_path') or media.get('filepath') or media.get('path', '')
                else:
                    media_id = str(media[0])
                    filename = media[2]  # Adjust indices based on schema
                    media_type = media[1]
                    related_type = media[10] if len(media) > 10 else ''
                    file_size = media[4]
                    created_at = media[9]
                    file_path = media[3] if len(media) > 3 else ''
                
                self.media_table.setItem(row, 0, QTableWidgetItem(media_id))
                
                # Add preview
                preview_item = QTableWidgetItem()
                if file_path:
                    # Convert relative path to absolute if needed
                    if file_path.startswith('media/'):
                        # This is a relative path from the bot
                        abs_file_path = os.path.join(os.path.dirname(self.media_folder), file_path)
                    else:
                        # This might be an absolute path
                        abs_file_path = file_path
                    
                    # Try to get thumbnail first only if we have a valid path
                    thumb_path = self.get_thumbnail_path(abs_file_path) if abs_file_path else None
                    
                    if media_type.lower() in ['photo', 'video', '3d_model']:
                        if thumb_path and os.path.exists(thumb_path):
                            pixmap = QPixmap(thumb_path)
                            if not pixmap.isNull():
                                scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                preview_item.setData(Qt.DecorationRole, scaled_pixmap)
                        elif media_type.lower() == 'photo' and abs_file_path and os.path.exists(abs_file_path):
                            # For photos only, try to load the original and scale it
                            pixmap = QPixmap(abs_file_path)
                            if not pixmap.isNull():
                                scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                preview_item.setData(Qt.DecorationRole, scaled_pixmap)
                        else:
                            # Add text indicator for video/3D without thumbnail
                            if media_type.lower() == 'video':
                                preview_item.setText('🎬')
                            elif media_type.lower() == '3d_model':
                                preview_item.setText('🎲')
                self.media_table.setItem(row, 1, preview_item)
                
                self.media_table.setItem(row, 2, QTableWidgetItem(filename))
                self.media_table.setItem(row, 3, QTableWidgetItem(media_type))
                self.media_table.setItem(row, 4, QTableWidgetItem(related_type))
                self.media_table.setItem(row, 5, QTableWidgetItem(str(created_at)[:10]))
                
                # Format file size
                if file_size:
                    if file_size > 1024*1024:
                        size_str = f"{file_size/(1024*1024):.1f} MB"
                    elif file_size > 1024:
                        size_str = f"{file_size/1024:.1f} KB"
                    else:
                        size_str = f"{file_size} bytes"
                    self.media_table.setItem(row, 6, QTableWidgetItem(size_str))
        
        self.update_status()
        self.filter_media()
    
    def filter_media(self):
        """Filter media list"""
        type_filter = self.type_combo.currentText()
        assoc_filter = self.assoc_combo.currentText()
        
        for row in range(self.media_table.rowCount()):
            show_row = True
            
            # Type filter
            if type_filter != self.tr("All"):
                media_type = self.media_table.item(row, 3).text()
                if media_type.lower() != type_filter.lower():
                    show_row = False
            
            # Association filter
            if assoc_filter != self.tr("All"):
                related_type = self.media_table.item(row, 4).text()
                if related_type.lower() != assoc_filter.lower():
                    show_row = False
            
            self.media_table.setRowHidden(row, not show_row)
        
        self.update_status()
    
    def update_status(self):
        """Update status label"""
        total = self.media_table.rowCount()
        visible = sum(1 for row in range(total) if not self.media_table.isRowHidden(row))
        
        if total == visible:
            self.status_label.setText(self.tr(f"Total media files: {total}"))
        else:
            self.status_label.setText(self.tr(f"Showing {visible} of {total} media files"))
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.media_table.selectedItems()) > 0
        self.delete_action.setEnabled(has_selection)
    
    def view_media(self, item):
        """View media file"""
        row = item.row()
        media_id = int(self.media_table.item(row, 0).text())
        
        print(f"DEBUG: Opening media ID {media_id} from row {row}")
        
        # Get file path and media type from database
        result = self.db_manager.execute_query(
            "SELECT file_path, media_type, file_name FROM media WHERE id = ?",
            (media_id,)
        )
        
        print(f"DEBUG: Query result for media ID {media_id}: {result}")
        
        if result:
            file_path = result[0]['file_path'] if isinstance(result[0], dict) else result[0][0]
            media_type = result[0]['media_type'] if isinstance(result[0], dict) else result[0][1]
            file_name = result[0]['file_name'] if isinstance(result[0], dict) else result[0][2]
            
            # Debug logging
            QgsMessageLog.logMessage(f"Opening media - ID: {media_id}, Name: {file_name}, Type: {media_type}, Path: {file_path}", "Shipwreck", level=0)
            print(f"DEBUG: Original path: {file_path}")
            print(f"DEBUG: Media folder: {self.media_folder}")
            
            # Convert relative path to absolute using media path manager
            abs_file_path = self.media_path_manager.get_absolute_path(file_path)
            
            # If media path manager couldn't resolve it, try direct path
            if not abs_file_path:
                if os.path.isabs(file_path) and os.path.exists(file_path):
                    abs_file_path = file_path
                else:
                    # Try with media folder as fallback
                    if file_path.startswith('media/'):
                        abs_file_path = os.path.join(os.path.dirname(self.media_folder), file_path)
                    else:
                        abs_file_path = os.path.join(self.media_folder, file_path)
            
            print(f"DEBUG: Final absolute path: {abs_file_path}")
            
            if not abs_file_path or not os.path.exists(abs_file_path):
                QMessageBox.warning(
                    self,
                    self.tr("File Not Found"),
                    self.tr(f"File not found: {file_path}")
                )
                return
            
            # Use absolute path for opening
            file_path = abs_file_path
            
            # Handle different media types
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Video files
            if media_type == 'video' or file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                try:
                    from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout
                    import sys
                    # Add UI directory to path for imports
                    ui_dir = os.path.dirname(__file__)
                    if ui_dir not in sys.path:
                        sys.path.insert(0, ui_dir)
                    
                    import opencv_video_player
                    
                    # Create dialog
                    dialog = QDialog(self)
                    dialog.setWindowTitle(os.path.basename(file_path))
                    dialog.setModal(True)
                    dialog.resize(800, 600)
                    
                    layout = QVBoxLayout()
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Create OpenCV video player
                    player = opencv_video_player.OpenCVVideoPlayer(dialog)
                    layout.addWidget(player)
                    
                    dialog.setLayout(layout)
                    
                    # Load video
                    player.load_video_file(file_path)
                    
                    dialog.exec_()
                    
                except ImportError as e:
                    QMessageBox.warning(self, "Import Error", 
                                      f"Could not load video player: {str(e)}\n\n"
                                      f"Make sure OpenCV is installed:\n"
                                      f"pip install opencv-python")
                    self.open_with_default_app(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Error opening video: {str(e)}")
                    self.open_with_default_app(file_path)
            
            # 3D model files
            elif media_type == '3d_model' or file_ext in ['.obj', '.stl', '.ply', '.dae']:
                try:
                    from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout
                    import sys
                    # Add UI directory to path for imports
                    ui_dir = os.path.dirname(__file__)
                    if ui_dir not in sys.path:
                        sys.path.insert(0, ui_dir)
                    
                    import model_viewer_widget
                    ModelViewerWidget = model_viewer_widget.ModelViewerWidget
                    
                    # Create dialog
                    dialog = QDialog(self)
                    dialog.setWindowTitle(os.path.basename(file_path))
                    dialog.setModal(True)
                    dialog.resize(800, 600)
                    
                    layout = QVBoxLayout()
                    
                    # Create 3D viewer
                    viewer = ModelViewerWidget(dialog)
                    layout.addWidget(viewer)
                    
                    dialog.setLayout(layout)
                    
                    # Load model after showing
                    dialog.show()
                    viewer.load_model(file_path)
                    
                    dialog.exec_()
                    
                except ImportError as e:
                    QMessageBox.warning(self, "Import Error", f"Could not load 3D viewer: {str(e)}")
                    self.open_with_default_app(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Error opening 3D model: {str(e)}")
                    self.open_with_default_app(file_path)
            
            # Image files - show in preview dialog
            elif media_type == 'photo' or file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                self.show_image_preview(file_path)
            
            # Other files - open with default app
            else:
                self.open_with_default_app(file_path)
    
    def open_with_default_app(self, file_path):
        """Open file with default application"""
        import subprocess
        import platform
        
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', file_path])
        elif platform.system() == 'Windows':
            os.startfile(file_path)
        else:  # Linux
            subprocess.call(['xdg-open', file_path])
    
    def show_image_preview(self, file_path):
        """Show image in a preview dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle(os.path.basename(file_path))
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Image label
        label = QLabel()
        pixmap = QPixmap(file_path)
        
        # Scale image to fit screen
        screen = QApplication.primaryScreen().availableGeometry()
        max_width = int(screen.width() * 0.8)
        max_height = int(screen.height() * 0.8)
        
        if pixmap.width() > max_width or pixmap.height() > max_height:
            pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        label.setPixmap(pixmap)
        layout.addWidget(label)
        
        # Close button
        close_btn = QPushButton(self.tr("Close"))
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def delete_media(self):
        """Delete selected media"""
        if not self.media_table.selectedItems():
            return
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Delete selected media file(s)?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Get selected media IDs
            selected_rows = set()
            for item in self.media_table.selectedItems():
                selected_rows.add(item.row())
            
            for row in selected_rows:
                media_id = int(self.media_table.item(row, 0).text())
                
                # Delete from database using Supabase
                success = self.db_manager.delete_media(media_id)
                if success:
                    QgsMessageLog.logMessage(f"Deleted media ID: {media_id}", 
                                           "MediaWidget", Qgis.Info)
                else:
                    QgsMessageLog.logMessage(f"Failed to delete media ID: {media_id}", 
                                           "MediaWidget", Qgis.Warning)
            
            self.refresh_data()
    
    def export_media_list(self):
        """Export media list with thumbnails"""
        if not self.current_site_id:
            QMessageBox.warning(
                self,
                self.tr("No Site Selected"),
                self.tr("Please select a site first")
            )
            return
        
        # Ask user for export format
        from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Export Media List"))
        layout = QVBoxLayout()
        
        html_radio = QRadioButton(self.tr("HTML with thumbnails"))
        html_radio.setChecked(True)
        pdf_radio = QRadioButton(self.tr("PDF with thumbnails"))
        
        layout.addWidget(QLabel(self.tr("Select export format:")))
        layout.addWidget(html_radio)
        layout.addWidget(pdf_radio)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_():
            # Get filename
            if html_radio.isChecked():
                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    self.tr("Save Media List"),
                    f"media_list_{self.site_combo.currentText()}.html",
                    "HTML Files (*.html)"
                )
                export_format = 'html'
            else:
                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    self.tr("Save Media List"),
                    f"media_list_{self.site_combo.currentText()}.pdf",
                    "PDF Files (*.pdf)"
                )
                export_format = 'pdf'
            
            if filename:
                try:
                    # Import exporter
                    import sys
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from utils.media_exporter import MediaExporter
                    
                    exporter = MediaExporter(self.db_manager)
                    
                    if export_format == 'html':
                        success = exporter.export_to_html(self.current_site_id, filename)
                    else:
                        success = exporter.export_to_pdf(self.current_site_id, filename)
                    
                    if success:
                        QMessageBox.information(
                            self,
                            self.tr("Success"),
                            self.tr(f"Media list exported to:\n{filename}")
                        )
                        
                        # Ask if user wants to open the file
                        reply = QMessageBox.question(
                            self,
                            self.tr("Open File"),
                            self.tr("Do you want to open the exported file?"),
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if reply == QMessageBox.Yes:
                            import subprocess
                            import platform
                            if platform.system() == 'Darwin':
                                subprocess.call(['open', filename])
                            elif platform.system() == 'Windows':
                                os.startfile(filename)
                            else:
                                subprocess.call(['xdg-open', filename])
                    else:
                        QMessageBox.warning(
                            self,
                            self.tr("No Media"),
                            self.tr("No media files found for this site")
                        )
                        
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        self.tr("Error"),
                        self.tr(f"Error exporting media list:\n{str(e)}")
                    )
    
    def tr(self, message):
        """Translate message"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('MediaWidget', message)