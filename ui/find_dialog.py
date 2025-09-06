# -*- coding: utf-8 -*-
"""Find entry dialog"""

from qgis.PyQt.QtCore import Qt, QDate, QSize, pyqtSignal
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                QFormLayout, QLineEdit, QTextEdit,
                                QComboBox, QDateEdit, QDoubleSpinBox, QSpinBox,
                                QDialogButtonBox, QLabel, QMessageBox,
                                QGroupBox, QListWidget, QListWidgetItem)
from qgis.PyQt.QtGui import QPixmap, QIcon, QDragEnterEvent, QDropEvent
from datetime import datetime
import os
import shutil

class MediaDropListWidget(QListWidget):
    """Custom QListWidget that accepts drag and drop of image files"""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # Check if any of the URLs are image files
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif')):
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path) and file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif')):
                    files.append(file_path)
            
            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class FindDialog(QDialog):
    """Dialog for adding/editing finds"""
    
    def __init__(self, db_manager, site_id, find_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.site_id = site_id
        self.find_id = find_id
        self.setWindowTitle(self.tr("Find Details"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.media_folder = self.setup_media_folder()
        
        self.init_ui()
        
        if find_id:
            self.load_find_data()
        else:
            self.generate_find_number()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # Find number
        self.find_number_edit = QLineEdit()
        form_layout.addRow(self.tr("Find Number:"), self.find_number_edit)
        
        # Inventory number (new field)
        self.inv_no_spin = QSpinBox()
        self.inv_no_spin.setMinimum(0)
        self.inv_no_spin.setMaximum(9999)
        form_layout.addRow(self.tr("Inventory No:"), self.inv_no_spin)
        
        # Year (new field)
        self.year_spin = QSpinBox()
        self.year_spin.setMinimum(2000)
        self.year_spin.setMaximum(2100)
        self.year_spin.setValue(QDate.currentDate().year())
        form_layout.addRow(self.tr("Year:"), self.year_spin)
        
        # Material type - updated with all types from database
        self.material_combo = QComboBox()
        self.material_combo.setEditable(True)  # Allow custom entries
        self.material_combo.addItems([
            "Black/Red Ware", "Stoneware", "Ceramic", "Porcelain", "Celadon", "Martaban",
            "Metal", "Wood", "Glass", "Stone Tool", "Bone", "Shell/Pearl",
            "Organic (Nut/Seed)", "Organic Material", "Fiber/Rope", "Resin",
            "Sediment", "Clay", "Horn", "Weight", "Mercury Jar", "Other"
        ])
        form_layout.addRow(self.tr("Material Type:"), self.material_combo)
        
        # Object type
        self.object_edit = QLineEdit()
        self.object_edit.setPlaceholderText("e.g., plate, coin, tool")
        form_layout.addRow(self.tr("Object Type:"), self.object_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        
        # Condition
        self.condition_combo = QComboBox()
        self.condition_combo.addItems([
            "Excellent", "Good", "Fair", "Poor", "Fragment"
        ])
        form_layout.addRow(self.tr("Condition:"), self.condition_combo)
        
        # Find date
        self.find_date = QDateEdit()
        self.find_date.setCalendarPopup(True)
        self.find_date.setDate(QDate.currentDate())
        form_layout.addRow(self.tr("Find Date:"), self.find_date)
        
        # Section (new field)
        self.section_edit = QLineEdit()
        self.section_edit.setPlaceholderText("e.g., F8N-F10N, EAST PORTION")
        form_layout.addRow(self.tr("Section:"), self.section_edit)
        
        # SU - Stratigraphic Unit (new field)
        self.su_edit = QLineEdit()
        self.su_edit.setPlaceholderText("e.g., 2, BAG 1")
        form_layout.addRow(self.tr("SU (Stratigraphic Unit):"), self.su_edit)
        
        # Depth
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setMaximum(999.99)
        self.depth_spin.setSuffix(" m")
        self.depth_spin.setDecimals(2)
        form_layout.addRow(self.tr("Depth:"), self.depth_spin)
        
        # Period
        self.period_edit = QLineEdit()
        form_layout.addRow(self.tr("Period:"), self.period_edit)
        
        # Quantity
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(9999)
        self.quantity_spin.setValue(1)
        form_layout.addRow(self.tr("Quantity:"), self.quantity_spin)
        
        # Dimensions (new field)
        self.dimensions_edit = QLineEdit()
        self.dimensions_edit.setPlaceholderText("e.g., thickness 0.5, 10x5x2 cm")
        form_layout.addRow(self.tr("Dimensions:"), self.dimensions_edit)
        
        # Context
        self.context_edit = QTextEdit()
        self.context_edit.setMaximumHeight(60)
        form_layout.addRow(self.tr("Context:"), self.context_edit)
        
        # Finder
        self.finder_edit = QLineEdit()
        form_layout.addRow(self.tr("Finder Name:"), self.finder_edit)
        
        # Storage
        self.storage_edit = QLineEdit()
        form_layout.addRow(self.tr("Storage Location:"), self.storage_edit)
        
        layout.addLayout(form_layout)
        
        # Media section - always show
        media_group = QGroupBox(self.tr("Associated Media (Drag && Drop Images Here)"))
        media_layout = QVBoxLayout()
        
        self.media_list = MediaDropListWidget()
        self.media_list.setIconSize(QSize(64, 64))
        self.media_list.setMaximumHeight(150)
        self.media_list.setFlow(QListWidget.LeftToRight)
        self.media_list.setWrapping(True)
        self.media_list.files_dropped.connect(self.handle_dropped_files)
        
        # Add hint label
        hint_label = QLabel(self.tr("Drag and drop image files here to add them"))
        hint_label.setStyleSheet("color: gray; font-style: italic;")
        hint_label.setAlignment(Qt.AlignCenter)
        
        media_layout.addWidget(self.media_list)
        media_layout.addWidget(hint_label)
        media_group.setLayout(media_layout)
        layout.addWidget(media_group)
        
        # Load associated media if editing
        if self.find_id:
            self.load_media_previews()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def generate_find_number(self):
        """Generate next find number"""
        # Get last find number for this site
        result = self.db_manager.execute_query(
            """SELECT find_number FROM finds 
               WHERE site_id = ? 
               ORDER BY id DESC LIMIT 1""",
            (self.site_id,)
        )
        
        if result:
            last_number = result[0][0] if isinstance(result[0], tuple) else result[0].get('find_number')
            # Try to extract number and increment
            try:
                import re
                match = re.search(r'(\d+)$', last_number)
                if match:
                    num = int(match.group(1)) + 1
                    prefix = last_number[:match.start()]
                    new_number = f"{prefix}{num:03d}"
                else:
                    new_number = f"F{datetime.now().year}-001"
            except:
                new_number = f"F{datetime.now().year}-001"
        else:
            new_number = f"F{datetime.now().year}-001"
        
        self.find_number_edit.setText(new_number)
    
    def load_find_data(self):
        """Load existing find data"""
        QgsMessageLog.logMessage(f"Loading find ID {self.find_id}", "Find Dialog", Qgis.Info)
        # Query specific fields to ensure we know the order - including new fields
        find = self.db_manager.execute_query(
            """SELECT id, site_id, find_number, material_type, object_type, 
                      description, condition, find_date, depth, period,
                      quantity, context_description, finder_name, storage_location, notes,
                      inv_no, year, section, su, dimensions
               FROM finds WHERE id = ?""",
            (self.find_id,)
        )
        
        if find and len(find) > 0:
            data = find[0]
            
            # Helper to get value by field name (handles both dict and tuple)
            def get_value(data, field_name):
                if isinstance(data, dict):
                    return data.get(field_name)
                else:
                    # Map tuple indices to field names - including new fields
                    field_map = {
                        'find_number': 2,
                        'material_type': 3,
                        'object_type': 4,
                        'description': 5,
                        'condition': 6,
                        'find_date': 7,
                        'depth': 8,
                        'period': 9,
                        'quantity': 10,
                        'context_description': 11,
                        'finder_name': 12,
                        'storage_location': 13,
                        'notes': 14,
                        'inv_no': 15,
                        'year': 16,
                        'section': 17,
                        'su': 18,
                        'dimensions': 19
                    }
                    if field_name in field_map:
                        idx = field_map[field_name]
                        if idx < len(data):
                            return data[idx]
                return None
            
            # Populate fields
            if get_value(data, 'find_number'):
                self.find_number_edit.setText(str(get_value(data, 'find_number')))
            
            if get_value(data, 'material_type'):
                idx = self.material_combo.findText(str(get_value(data, 'material_type')))
                if idx >= 0:
                    self.material_combo.setCurrentIndex(idx)
            
            if get_value(data, 'object_type'):
                self.object_edit.setText(str(get_value(data, 'object_type')))
            
            if get_value(data, 'description'):
                self.description_edit.setText(str(get_value(data, 'description')))
            
            if get_value(data, 'condition'):
                idx = self.condition_combo.findText(str(get_value(data, 'condition')))
                if idx >= 0:
                    self.condition_combo.setCurrentIndex(idx)
            
            if get_value(data, 'find_date'):
                date_str = str(get_value(data, 'find_date'))
                date = QDate.fromString(date_str, 'yyyy-MM-dd')
                if date.isValid():
                    self.find_date.setDate(date)
            
            if get_value(data, 'depth'):
                self.depth_spin.setValue(float(get_value(data, 'depth')))
            
            if get_value(data, 'period'):
                self.period_edit.setText(str(get_value(data, 'period')))
            
            if get_value(data, 'quantity'):
                self.quantity_spin.setValue(int(get_value(data, 'quantity')))
            
            if get_value(data, 'context_description'):
                self.context_edit.setText(str(get_value(data, 'context_description')))
            
            if get_value(data, 'finder_name'):
                self.finder_edit.setText(str(get_value(data, 'finder_name')))
            
            if get_value(data, 'storage_location'):
                self.storage_edit.setText(str(get_value(data, 'storage_location')))
            
            # Load new fields
            if get_value(data, 'inv_no'):
                self.inv_no_spin.setValue(int(get_value(data, 'inv_no')))
            
            if get_value(data, 'year'):
                self.year_spin.setValue(int(get_value(data, 'year')))
            
            if get_value(data, 'section'):
                self.section_edit.setText(str(get_value(data, 'section')))
            
            if get_value(data, 'su'):
                self.su_edit.setText(str(get_value(data, 'su')))
            
            if get_value(data, 'dimensions'):
                self.dimensions_edit.setText(str(get_value(data, 'dimensions')))
    
    def load_media_previews(self):
        """Load media previews for the find"""
        if not self.find_id:
            return
        
        try:
            QgsMessageLog.logMessage(f"Loading media for find {self.find_id}", "Find Dialog", Qgis.Info)
            # First get media relations for this find
            relations = self.db_manager.execute_query(
                "SELECT media_id FROM media_relations WHERE related_type = 'find' AND related_id = ?",
                (self.find_id,)
            )
            
            QgsMessageLog.logMessage(f"Found {len(relations) if relations else 0} media relations", "Find Dialog", Qgis.Info)
            
            if not relations:
                QgsMessageLog.logMessage(f"No media relations found for find {self.find_id}", "Find Dialog", Qgis.Warning)
                return
                
            # Get all media IDs
            media_ids = [r['media_id'] if isinstance(r, dict) else r[0] for r in relations]
            QgsMessageLog.logMessage(f"Media IDs: {media_ids}", "Find Dialog", Qgis.Info)
            
            # Get media files for these IDs
            media_files = []
            for media_id in media_ids:
                media_result = self.db_manager.execute_query(
                    "SELECT id, file_name, file_path, media_type FROM media WHERE id = ?",
                    (media_id,)
                )
                if media_result:
                    media_files.extend(media_result)
                    QgsMessageLog.logMessage(f"Found media {media_id}: {media_result[0]}", "Find Dialog", Qgis.Info)
        
        except Exception as e:
            QgsMessageLog.logMessage(f"Error loading media for find {self.find_id}: {e}", "Find Dialog", Qgis.Critical)
            media_files = []
        
        if media_files:
            for media in media_files:
                QgsMessageLog.logMessage(f"Processing media record: {media}", "Find Dialog", Qgis.Info)
                if isinstance(media, dict):
                    filename = media['file_name']
                    file_path = media['file_path']
                    media_type = media['media_type']
                else:
                    filename = media[1]
                    file_path = media[2]
                    media_type = media[3]
                
                QgsMessageLog.logMessage(f"Media details - filename: {filename}, file_path: {file_path}, type: {media_type}", "Find Dialog", Qgis.Info)
                
                item = QListWidgetItem(filename)
                item.setToolTip(filename)
                
                # Set thumbnail for images
                if media_type == 'photo' and file_path:
                    pixmap = None
                    
                    # Check if it's an absolute path
                    if os.path.isabs(file_path) and os.path.exists(file_path):
                        pixmap = QPixmap(file_path)
                    else:
                        # It's a relative path, try different combinations
                        # First, just the relative path from current directory
                        if os.path.exists(file_path):
                            pixmap = QPixmap(file_path)
                        else:
                            # Try with configured media base path
                            media_base = self.db_manager.get_setting('media_base_path')
                            QgsMessageLog.logMessage(f"Retrieved media_base_path: {media_base}", "Find Dialog", Qgis.Info)
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
                                QgsMessageLog.logMessage(f"Path construction:", "Find Dialog", Qgis.Info)
                                QgsMessageLog.logMessage(f"  - base_path: {base_path}", "Find Dialog", Qgis.Info)
                                QgsMessageLog.logMessage(f"  - file_path from DB: {file_path}", "Find Dialog", Qgis.Info)
                                QgsMessageLog.logMessage(f"  - normalized_file_path: {normalized_file_path}", "Find Dialog", Qgis.Info)
                                QgsMessageLog.logMessage(f"  - full_drive_path: {full_drive_path}", "Find Dialog", Qgis.Info)
                                QgsMessageLog.logMessage(f"  - exists: {os.path.exists(full_drive_path)}", "Find Dialog", Qgis.Info)
                            else:
                                # No configured path, try relative to current directory
                                full_drive_path = file_path
                                QgsMessageLog.logMessage(f"No media_base_path configured, using relative path", "Find Dialog", Qgis.Warning)
                                # Show a message to the user to configure their path
                                if not hasattr(self, '_path_warning_shown'):
                                    self._path_warning_shown = True
                                    QMessageBox.warning(self, self.tr("Configure Media Path"), 
                                        self.tr("No media path configured.\n\nPlease go to Shipwreck Excavation → Settings and set your local Google Drive path."))
                            
                            if os.path.exists(full_drive_path):
                                pixmap = QPixmap(full_drive_path)
                                QgsMessageLog.logMessage(f"Found image at {full_drive_path}", "Find Dialog", Qgis.Success)
                            else:
                                QgsMessageLog.logMessage(f"Image not found. Tried paths:", "Find Dialog", Qgis.Warning)
                                QgsMessageLog.logMessage(f"  - {file_path}", "Find Dialog", Qgis.Warning)
                                QgsMessageLog.logMessage(f"  - {full_drive_path}", "Find Dialog", Qgis.Warning)
                    
                    if pixmap and not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(scaled_pixmap))
                    else:
                        QgsMessageLog.logMessage(f"Failed to load pixmap for {file_path}", "Find Dialog", Qgis.Warning)
                
                self.media_list.addItem(item)
                QgsMessageLog.logMessage(f"Added media item: {filename}", "Find Dialog", Qgis.Info)
        
        QgsMessageLog.logMessage(f"Total media items loaded: {self.media_list.count()}", "Find Dialog", Qgis.Info)
    
    def get_thumbnail_path(self, image_path):
        """Get thumbnail path for image"""
        # Assuming thumbnails are stored in a thumbnails folder
        base_dir = os.path.dirname(os.path.dirname(image_path))
        filename = os.path.basename(image_path)
        return os.path.join(base_dir, 'thumbnails', f'thumb_{filename}')
    
    def setup_media_folder(self):
        """Setup media storage folder"""
        # Get database folder
        db_path = self.db_manager.db_path
        if db_path:
            media_folder = os.path.join(os.path.dirname(db_path), "media")
        else:
            media_folder = os.path.expanduser("~/Documents/ShipwreckMedia")
        
        # Create folder structure if it doesn't exist
        for folder in [media_folder, os.path.join(media_folder, 'photos'), 
                      os.path.join(media_folder, 'thumbnails')]:
            if not os.path.exists(folder):
                os.makedirs(folder)
                
        return media_folder
    
    def handle_dropped_files(self, files):
        """Handle dropped image files"""
        added = 0
        for file_path in files:
            if self.add_media_file(file_path):
                added += 1
        
        if added > 0:
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr(f"Added {added} image(s) to this find")
            )
    
    def add_media_file(self, file_path):
        """Add a media file"""
        try:
            # Copy file to media folder
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{timestamp}_{filename}"
            dest_path = os.path.join(self.media_folder, 'photos', new_filename)
            
            shutil.copy2(file_path, dest_path)
            
            # Create thumbnail
            self.create_thumbnail(dest_path)
            
            # Add to list widget immediately
            item = QListWidgetItem(filename)
            item.setToolTip(filename)
            
            # Set thumbnail
            thumb_path = self.get_thumbnail_path(dest_path)
            if os.path.exists(thumb_path):
                pixmap = QPixmap(thumb_path)
            else:
                pixmap = QPixmap(dest_path)
            
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(scaled_pixmap))
            
            # Store file info for later saving
            item.setData(Qt.UserRole, {
                'file_name': new_filename,
                'file_path': dest_path,
                'file_size': os.path.getsize(file_path)
            })
            
            self.media_list.addItem(item)
            return True
            
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr(f"Failed to add image: {str(e)}")
            )
            return False
    
    def create_thumbnail(self, image_path):
        """Create thumbnail for image"""
        try:
            from PIL import Image
            
            thumb_path = self.get_thumbnail_path(image_path)
            
            with Image.open(image_path) as img:
                img.thumbnail((150, 150))
                img.save(thumb_path)
                
        except ImportError:
            # PIL not available, try Qt
            try:
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    thumb_path = self.get_thumbnail_path(image_path)
                    scaled = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    scaled.save(thumb_path)
            except:
                pass
        except Exception:
            pass
    
    def get_find_data(self):
        """Get find data from form"""
        return {
            'site_id': self.site_id,
            'find_number': self.find_number_edit.text(),
            'material_type': self.material_combo.currentText(),
            'object_type': self.object_edit.text(),
            'description': self.description_edit.toPlainText(),
            'condition': self.condition_combo.currentText(),
            'find_date': self.find_date.date().toString('yyyy-MM-dd'),
            'depth': self.depth_spin.value() if self.depth_spin.value() > 0 else None,
            'period': self.period_edit.text(),
            'quantity': int(self.quantity_spin.value()),
            'context_description': self.context_edit.toPlainText(),
            'finder_name': self.finder_edit.text(),
            'storage_location': self.storage_edit.text(),
            # New fields
            'inv_no': self.inv_no_spin.value() if self.inv_no_spin.value() > 0 else None,
            'year': self.year_spin.value(),
            'section': self.section_edit.text() if self.section_edit.text() else None,
            'su': self.su_edit.text() if self.su_edit.text() else None,
            'dimensions': self.dimensions_edit.text() if self.dimensions_edit.text() else None
        }
    
    def accept(self):
        """Validate and accept"""
        if not self.find_number_edit.text():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Find number is required")
            )
            return
        
        # Save find data first
        find_data = self.get_find_data()
        
        if self.find_id:
            # Update existing find
            set_clause = ', '.join([f"{k} = ?" for k in find_data.keys()])
            values = list(find_data.values()) + [self.find_id]
            
            success = self.db_manager.execute_update(
                f"UPDATE finds SET {set_clause} WHERE id = ?",
                values
            )
            find_id = self.find_id if success else None
        else:
            # Insert new find
            find_id = self.db_manager.add_find(find_data)
        
        if find_id:
            # Save any new media files
            for i in range(self.media_list.count()):
                item = self.media_list.item(i)
                media_data = item.data(Qt.UserRole)
                
                # Only process items with user data (newly added)
                if media_data:
                    media_record = {
                        'media_type': 'photo',
                        'file_name': media_data['file_name'],
                        'file_path': media_data['file_path'],
                        'file_size': media_data['file_size'],
                        'description': f"Photo for find {self.find_number_edit.text()}",
                        'capture_date': datetime.now().isoformat()  # Convert to ISO string for JSON serialization
                    }
                    
                    self.db_manager.add_media(media_record, 'find', find_id)
        
        super().accept()
    
    def tr(self, message):
        """Translate message"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('FindDialog', message)