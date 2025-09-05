# -*- coding: utf-8 -*-
"""Dive log management widget"""

from qgis.PyQt.QtCore import Qt, QDate, QTime, pyqtSignal, QSize
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QToolBar,
                                QLineEdit, QLabel, QMessageBox, QHeaderView,
                                QFormLayout, QDialog, QDialogButtonBox,
                                QTextEdit, QDateEdit, QTimeEdit, QSpinBox, 
                                QDoubleSpinBox, QComboBox, QListWidget,
                                QListWidgetItem, QGroupBox, QCheckBox, 
                                QTabWidget, QGridLayout)
from qgis.PyQt.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent
from datetime import datetime, date
import os
import shutil
import sys

# Add parent directory to path for imports
plugin_dir = os.path.dirname(os.path.dirname(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from ui.media_list_widget import MediaListWidget


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
                if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
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
                if os.path.isfile(file_path) and file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    files.append(file_path)
            
            if files:
                self.files_dropped.emit(files)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class DiveLogDialog(QDialog):
    """Dialog for adding/editing dive logs"""
    
    def __init__(self, db_manager, site_id, dive_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.site_id = site_id
        self.dive_id = dive_id
        self.setWindowTitle(self.tr("Dive Log Entry"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.resize(500, 450)
        self.media_folder = self.setup_media_folder()
        
        # Initialize team_members before init_ui
        self.team_members = []
        
        self.init_ui()
        
        if dive_id:
            self.load_dive_data()
        else:
            self.generate_dive_number()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Tab 1: Basic Info
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        
        # Basic info in compact 2-column layout
        basic_form = QFormLayout()
        basic_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # Row 1: Dive number and Date
        row1_layout = QHBoxLayout()
        self.dive_number_edit = QLineEdit()
        self.dive_number_edit.setMaximumWidth(150)
        row1_layout.addWidget(QLabel(self.tr("Dive Number:")))
        row1_layout.addWidget(self.dive_number_edit)
        row1_layout.addSpacing(20)
        
        self.dive_date = QDateEdit()
        self.dive_date.setCalendarPopup(True)
        self.dive_date.setDate(QDate.currentDate())
        row1_layout.addWidget(QLabel(self.tr("Date:")))
        row1_layout.addWidget(self.dive_date)
        row1_layout.addStretch()
        basic_form.addRow(row1_layout)
        
        # Row 2: Times
        time_layout = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        time_layout.addWidget(QLabel(self.tr("Start Time:")))
        time_layout.addWidget(self.start_time)
        time_layout.addSpacing(20)
        
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        time_layout.addWidget(QLabel(self.tr("End Time:")))
        time_layout.addWidget(self.end_time)
        time_layout.addStretch()
        basic_form.addRow(time_layout)
        
        # Row 3: Depths
        depth_layout = QHBoxLayout()
        self.max_depth = QDoubleSpinBox()
        self.max_depth.setMaximum(999.9)
        self.max_depth.setSuffix(" m")
        self.max_depth.setDecimals(1)
        depth_layout.addWidget(QLabel(self.tr("Max Depth:")))
        depth_layout.addWidget(self.max_depth)
        depth_layout.addSpacing(20)
        
        self.avg_depth = QDoubleSpinBox()
        self.avg_depth.setMaximum(999.9)
        self.avg_depth.setSuffix(" m")
        self.avg_depth.setDecimals(1)
        depth_layout.addWidget(QLabel(self.tr("Avg Depth:")))
        depth_layout.addWidget(self.avg_depth)
        depth_layout.addStretch()
        basic_form.addRow(depth_layout)
        
        basic_layout.addLayout(basic_form)
        
        # Conditions group
        conditions_group = QGroupBox(self.tr("Conditions"))
        conditions_layout = QGridLayout()
        
        # Water temp
        self.water_temp = QDoubleSpinBox()
        self.water_temp.setRange(-5, 40)
        self.water_temp.setSuffix(" °C")
        self.water_temp.setDecimals(1)
        conditions_layout.addWidget(QLabel(self.tr("Water Temp:")), 0, 0)
        conditions_layout.addWidget(self.water_temp, 0, 1)
        
        # Visibility
        self.visibility = QDoubleSpinBox()
        self.visibility.setMaximum(100)
        self.visibility.setSuffix(" m")
        self.visibility.setDecimals(1)
        conditions_layout.addWidget(QLabel(self.tr("Visibility:")), 0, 2)
        conditions_layout.addWidget(self.visibility, 0, 3)
        
        # Current
        self.current_combo = QComboBox()
        self.current_combo.addItems(["None", "Weak", "Moderate", "Strong", "Very Strong"])
        conditions_layout.addWidget(QLabel(self.tr("Current:")), 1, 0)
        conditions_layout.addWidget(self.current_combo, 1, 1, 1, 2)
        
        # Weather
        self.weather_edit = QLineEdit()
        self.weather_edit.setPlaceholderText("e.g., Sunny, calm seas")
        conditions_layout.addWidget(QLabel(self.tr("Weather:")), 2, 0)
        conditions_layout.addWidget(self.weather_edit, 2, 1, 1, 3)
        
        conditions_layout.setColumnStretch(1, 1)
        conditions_layout.setColumnStretch(3, 1)
        conditions_group.setLayout(conditions_layout)
        basic_layout.addWidget(conditions_group)
        
        basic_layout.addStretch()
        basic_tab.setLayout(basic_layout)
        self.tabs.addTab(basic_tab, self.tr("Basic Info"))
        
        # Tab 2: Work Details
        work_tab = QWidget()
        work_layout = QVBoxLayout()
        
        # Objectives
        work_layout.addWidget(QLabel(self.tr("Objectives:")))
        self.objectives_edit = QTextEdit()
        self.objectives_edit.setMaximumHeight(80)
        self.objectives_edit.setPlaceholderText(self.tr("What was planned for this dive..."))
        work_layout.addWidget(self.objectives_edit)
        
        # Work completed
        work_layout.addWidget(QLabel(self.tr("Work Done:")))
        self.work_edit = QTextEdit()
        self.work_edit.setMaximumHeight(80)
        self.work_edit.setPlaceholderText(self.tr("What was actually accomplished..."))
        work_layout.addWidget(self.work_edit)
        
        # Findings
        work_layout.addWidget(QLabel(self.tr("Findings:")))
        self.findings_edit = QTextEdit()
        self.findings_edit.setMaximumHeight(80)
        self.findings_edit.setPlaceholderText(self.tr("Summary of finds or observations..."))
        work_layout.addWidget(self.findings_edit)
        
        # Equipment
        equip_layout = QHBoxLayout()
        equip_layout.addWidget(QLabel(self.tr("Equipment:")))
        self.equipment_edit = QLineEdit()
        self.equipment_edit.setPlaceholderText("e.g., Cameras, dredge, measuring tools")
        equip_layout.addWidget(self.equipment_edit)
        work_layout.addLayout(equip_layout)
        
        work_layout.addStretch()
        work_tab.setLayout(work_layout)
        self.tabs.addTab(work_tab, self.tr("Work Details"))
        
        # Tab 3: Team & Media
        team_tab = QWidget()
        team_layout = QVBoxLayout()
        
        # Team section
        team_group = QGroupBox(self.tr("Dive Team"))
        team_group_layout = QVBoxLayout()
        
        # Worker selection
        worker_layout = QHBoxLayout()
        self.worker_combo = QComboBox()
        self.load_workers()
        worker_layout.addWidget(self.worker_combo)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems([
            "Dive Supervisor", "Archaeologist", "Photographer", 
            "Safety Diver", "Support Diver"
        ])
        worker_layout.addWidget(self.role_combo)
        
        self.add_worker_btn = QPushButton(self.tr("Add"))
        self.add_worker_btn.clicked.connect(self.add_team_member)
        worker_layout.addWidget(self.add_worker_btn)
        
        team_group_layout.addLayout(worker_layout)
        
        # Team list
        self.team_list = QListWidget()
        self.team_list.setMaximumHeight(100)
        team_group_layout.addWidget(self.team_list)
        
        # Remove button for team members
        self.remove_worker_btn = QPushButton(self.tr("Remove Selected"))
        self.remove_worker_btn.clicked.connect(self.remove_team_member)
        team_group_layout.addWidget(self.remove_worker_btn)
        
        team_group.setLayout(team_group_layout)
        team_layout.addWidget(team_group)
        
        # Media section
        media_group = QGroupBox(self.tr("Media (Drag && Drop)"))
        media_layout = QVBoxLayout()
        
        self.media_list = MediaDropListWidget()
        self.media_list.setIconSize(QSize(64, 64))
        self.media_list.setMaximumHeight(120)
        self.media_list.setFlow(QListWidget.LeftToRight)
        self.media_list.setWrapping(True)
        self.media_list.files_dropped.connect(self.handle_dropped_files)
        
        media_layout.addWidget(self.media_list)
        media_group.setLayout(media_layout)
        team_layout.addWidget(media_group)
        
        # Notes
        team_layout.addWidget(QLabel(self.tr("Notes:")))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        team_layout.addWidget(self.notes_edit)
        
        team_layout.addStretch()
        team_tab.setLayout(team_layout)
        self.tabs.addTab(team_tab, self.tr("Team & Notes"))
        
        layout.addWidget(self.tabs)
        
        # Load associated media if editing
        if self.dive_id:
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
    
    def generate_dive_number(self):
        """Generate next dive number"""
        # First get site code
        sites = self.db_manager.execute_query(
            "SELECT site_code FROM sites WHERE id = ?",
            (self.site_id,)
        )
        
        site_code = "SITE"
        if sites:
            site_code = sites[0]['site_code'] if isinstance(sites[0], dict) else sites[0][0]
        
        # Get last dive number for this site
        result = self.db_manager.execute_query(
            """SELECT dive_number FROM dive_logs 
               WHERE site_id = ? 
               ORDER BY dive_date DESC, dive_number DESC 
               LIMIT 1""",
            (self.site_id,)
        )
        
        if result:
            last_number = result[0][0] if isinstance(result[0], tuple) else result[0].get('dive_number')
            # Extract number and increment
            try:
                # Try to find the last numeric part
                import re
                numbers = re.findall(r'\d+', last_number)
                if numbers:
                    # Get the last number and increment it
                    last_num = int(numbers[-1])
                    new_num = last_num + 1
                    # Replace the last number with the new one
                    new_number = re.sub(r'\d+(?!.*\d)', f'{new_num:03d}', last_number)
                else:
                    # No number found, append 001
                    new_number = f"{last_number}-001"
            except:
                new_number = f"{site_code}-{date.today().year}-001"
        else:
            # First dive for this site
            new_number = f"{site_code}-{date.today().year}-001"
        
        self.dive_number_edit.setText(new_number)
    
    def load_workers(self):
        """Load active workers"""
        workers = self.db_manager.execute_query(
            "SELECT id, full_name FROM workers WHERE active = 1 ORDER BY full_name"
        )
        
        self.worker_combo.clear()
        self.worker_combo.addItem(self.tr("Select worker..."), None)
        
        if workers:
            for worker in workers:
                if isinstance(worker, dict):
                    self.worker_combo.addItem(worker['full_name'], worker['id'])
                else:
                    self.worker_combo.addItem(worker[1], worker[0])
    
    def add_team_member(self):
        """Add team member to list"""
        worker_id = self.worker_combo.currentData()
        if not worker_id:
            return
        
        worker_name = self.worker_combo.currentText()
        role = self.role_combo.currentText()
        
        # Check if already added
        for member in self.team_members:
            if member['worker_id'] == worker_id:
                QMessageBox.warning(
                    self,
                    self.tr("Duplicate"),
                    self.tr("This worker is already in the team")
                )
                return
        
        # Add to list
        item_text = f"{worker_name} - {role}"
        self.team_list.addItem(item_text)
        
        self.team_members.append({
            'worker_id': worker_id,
            'role': role
        })
        
        # Reset combo
        self.worker_combo.setCurrentIndex(0)
    
    def remove_team_member(self):
        """Remove selected team member from list"""
        current_row = self.team_list.currentRow()
        if current_row >= 0:
            # Remove from list widget
            self.team_list.takeItem(current_row)
            # Remove from team_members list
            if current_row < len(self.team_members):
                self.team_members.pop(current_row)
    
    def load_dive_data(self):
        """Load existing dive data"""
        try:
            print(f"DEBUG DiveLogDialog: Loading dive ID {self.dive_id}")
            # Query specific fields to ensure we know the order
            dive = self.db_manager.execute_query(
                """SELECT id, site_id, dive_number, dive_date, dive_start, dive_end,
                          max_depth, avg_depth, water_temp, visibility, current_strength,
                          weather_conditions, dive_objectives, work_completed, findings_summary,
                          equipment_used, notes
                   FROM dive_logs WHERE id = ?""",
                (self.dive_id,)
            )
            print(f"DEBUG DiveLogDialog: Query returned {len(dive) if dive else 0} results")
        except Exception as e:
            print(f"ERROR DiveLogDialog: Failed to load dive data: {e}")
            QMessageBox.warning(self, self.tr("Error"), self.tr(f"Failed to load dive data: {str(e)}"))
            return
        
        if dive and len(dive) > 0:
            data = dive[0]
            
            # Map tuple indices to field names
            field_map = {
                'dive_number': 2,
                'dive_date': 3,
                'dive_start': 4,
                'dive_end': 5,
                'max_depth': 6,
                'avg_depth': 7,
                'water_temp': 8,
                'visibility': 9,
                'current_strength': 10,
                'weather_conditions': 11,
                'dive_objectives': 12,
                'work_completed': 13,
                'findings_summary': 14,
                'equipment_used': 15,
                'notes': 16
            }
            
            # Helper to get value by field name
            def get_value(data, field_name):
                # Check if data is a dictionary (from Supabase)
                if isinstance(data, dict):
                    return data.get(field_name)
                # Otherwise it's a tuple/list from direct query
                elif field_name in field_map:
                    idx = field_map[field_name]
                    if idx < len(data):
                        return data[idx]
                return None
            
            # Populate fields
            if get_value(data, 'dive_number'):
                self.dive_number_edit.setText(str(get_value(data, 'dive_number')))
            
            if get_value(data, 'dive_date'):
                date_str = str(get_value(data, 'dive_date'))
                date = QDate.fromString(date_str, 'yyyy-MM-dd')
                if date.isValid():
                    self.dive_date.setDate(date)
            
            if get_value(data, 'dive_start'):
                time_str = str(get_value(data, 'dive_start'))
                time = QTime.fromString(time_str, 'HH:mm:ss')
                if not time.isValid():
                    time = QTime.fromString(time_str, 'HH:mm')
                if time.isValid():
                    self.start_time.setTime(time)
            
            if get_value(data, 'dive_end'):
                time_str = str(get_value(data, 'dive_end'))
                time = QTime.fromString(time_str, 'HH:mm:ss')
                if not time.isValid():
                    time = QTime.fromString(time_str, 'HH:mm')
                if time.isValid():
                    self.end_time.setTime(time)
            
            if get_value(data, 'max_depth'):
                self.max_depth.setValue(float(get_value(data, 'max_depth')))
            
            if get_value(data, 'avg_depth'):
                self.avg_depth.setValue(float(get_value(data, 'avg_depth')))
            
            if get_value(data, 'water_temp'):
                self.water_temp.setValue(float(get_value(data, 'water_temp')))
            
            if get_value(data, 'visibility'):
                self.visibility.setValue(float(get_value(data, 'visibility')))
            
            if get_value(data, 'current_strength'):
                idx = self.current_combo.findText(str(get_value(data, 'current_strength')))
                if idx >= 0:
                    self.current_combo.setCurrentIndex(idx)
            
            if get_value(data, 'weather_conditions'):
                self.weather_edit.setText(str(get_value(data, 'weather_conditions')))
            
            if get_value(data, 'dive_objectives'):
                self.objectives_edit.setText(str(get_value(data, 'dive_objectives')))
            
            if get_value(data, 'work_completed'):
                self.work_edit.setText(str(get_value(data, 'work_completed')))
            
            if get_value(data, 'findings_summary'):
                self.findings_edit.setText(str(get_value(data, 'findings_summary')))
            
            if get_value(data, 'equipment_used'):
                self.equipment_edit.setText(str(get_value(data, 'equipment_used')))
            
            if get_value(data, 'notes'):
                self.notes_edit.setText(str(get_value(data, 'notes')))
            
            # Load team members
            team_members = self.db_manager.execute_query(
                "SELECT * FROM dive_team WHERE dive_id = ?",
                (self.dive_id,)
            )
            
            if team_members:
                for member in team_members:
                    worker_id = member['worker_id'] if isinstance(member, dict) else member[2]
                    role = member['role'] if isinstance(member, dict) else member[3]
                    
                    # Get worker name
                    workers = self.db_manager.execute_query(
                        "SELECT full_name FROM workers WHERE id = ?",
                        (worker_id,)
                    )
                    
                    if workers:
                        worker_name = workers[0]['full_name'] if isinstance(workers[0], dict) else workers[0][0]
                        item_text = f"{worker_name} - {role}"
                        self.team_list.addItem(item_text)
                        self.team_members.append({
                            'worker_id': worker_id,
                            'role': role
                        })
    
    def load_media_previews(self):
        """Load media previews for the dive log"""
        if not self.dive_id:
            return
            
        # Use the database manager method for media
        media_files = self.db_manager.get_media_for_item('dive_log', self.dive_id)
        
        if media_files:
            for media in media_files:
                if isinstance(media, dict):
                    filename = media['file_name']
                    file_path = media['file_path']
                    media_type = media['media_type']
                else:
                    filename = media[1]
                    file_path = media[2]
                    media_type = media[3]
                
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
                            else:
                                # No configured path, try relative to current directory
                                full_drive_path = file_path
                            if os.path.exists(full_drive_path):
                                pixmap = QPixmap(full_drive_path)
                    
                    if pixmap and not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(scaled_pixmap))
                
                self.media_list.addItem(item)
    
    def get_thumbnail_path(self, image_path):
        """Get thumbnail path for image"""
        # Assuming thumbnails are stored in a thumbnails folder
        base_dir = os.path.dirname(os.path.dirname(image_path))
        filename = os.path.basename(image_path)
        return os.path.join(base_dir, 'thumbnails', f'thumb_{filename}')
    
    def setup_media_folder(self):
        """Setup media storage folder"""
        try:
            # Try to get configured media path from settings
            media_path = self.db_manager.get_setting('media_base_path') if hasattr(self.db_manager, 'get_setting') else None
            
            if media_path and os.path.exists(media_path):
                # Use configured path
                if media_path.endswith('/media') or media_path.endswith('\\media'):
                    media_folder = media_path
                else:
                    media_folder = os.path.join(media_path, "media")
            elif self.db_manager.db_path:
                # Fallback to db_path
                media_folder = os.path.join(os.path.dirname(self.db_manager.db_path), "media")
            else:
                # Last resort - use default folder
                media_folder = os.path.expanduser("~/Documents/ShipwreckMedia")
            
            # Create folder structure if it doesn't exist
            for folder in [media_folder, os.path.join(media_folder, 'photos'), 
                          os.path.join(media_folder, 'thumbnails')]:
                if not os.path.exists(folder):
                    try:
                        os.makedirs(folder)
                    except Exception as e:
                        print(f"Warning: Could not create media folder {folder}: {e}")
                    
            return media_folder
        except Exception as e:
            print(f"Warning: Error setting up media folder: {e}")
            # Return a safe default
            return os.path.expanduser("~/Documents/ShipwreckMedia")
    
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
                self.tr(f"Added {added} image(s) to this dive log")
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
    
    def get_dive_data(self):
        """Get dive data from form"""
        return {
            'site_id': self.site_id,
            'dive_number': self.dive_number_edit.text(),
            'dive_date': self.dive_date.date().toString('yyyy-MM-dd'),
            'dive_start': self.start_time.time().toString('HH:mm:ss'),
            'dive_end': self.end_time.time().toString('HH:mm:ss'),
            'max_depth': self.max_depth.value() if self.max_depth.value() > 0 else None,
            'avg_depth': self.avg_depth.value() if self.avg_depth.value() > 0 else None,
            'water_temp': self.water_temp.value() if self.water_temp.value() != 0 else None,
            'visibility': self.visibility.value() if self.visibility.value() > 0 else None,
            'current_strength': self.current_combo.currentText(),
            'weather_conditions': self.weather_edit.text(),
            'dive_objectives': self.objectives_edit.toPlainText(),
            'work_completed': self.work_edit.toPlainText(),
            'findings_summary': self.findings_edit.toPlainText(),
            'equipment_used': self.equipment_edit.text(),
            'notes': self.notes_edit.toPlainText()
        }
    
    def accept(self):
        """Validate and save"""
        if not self.dive_number_edit.text():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Dive number is required")
            )
            return
        
        # Get dive data
        dive_data = self.get_dive_data()
        
        if self.dive_id:
            # Update existing dive
            set_clause = ', '.join([f"{k} = ?" for k in dive_data.keys()])
            values = list(dive_data.values()) + [self.dive_id]
            
            success = self.db_manager.execute_update(
                f"UPDATE dive_logs SET {set_clause} WHERE id = ?",
                values
            )
            dive_id = self.dive_id if success else None
            
            # Update team members
            if dive_id:
                # Delete existing team members
                self.db_manager.execute_update(
                    "DELETE FROM dive_team WHERE dive_id = ?",
                    (dive_id,)
                )
                
                # Add new team members
                print(f"DEBUG: Saving {len(self.team_members)} team members for dive {dive_id}")
                for i, member in enumerate(self.team_members):
                    print(f"DEBUG: Team member {i+1}: worker_id={member['worker_id']}, role={member['role']}")
                    self.db_manager.execute_update(
                        """INSERT INTO dive_team (dive_id, worker_id, role)
                           VALUES (?, ?, ?)""",
                        (dive_id, member['worker_id'], member['role'])
                    )
        else:
            # Insert new dive
            columns = ', '.join(dive_data.keys())
            placeholders = ', '.join(['?' for _ in dive_data])
            
            dive_id = self.db_manager.execute_update(
                f"INSERT INTO dive_logs ({columns}) VALUES ({placeholders})",
                list(dive_data.values())
            )
            
            if dive_id:
                # Add team members
                for member in self.team_members:
                    self.db_manager.execute_update(
                        """INSERT INTO dive_team (dive_id, worker_id, role)
                           VALUES (?, ?, ?)""",
                        (dive_id, member['worker_id'], member['role'])
                    )
        
        if dive_id:
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
                        'description': f"Photo for dive {self.dive_number_edit.text()}",
                        'capture_date': datetime.now()
                    }
                    
                    self.db_manager.add_media(media_record, 'dive', dive_id)
        
        super().accept()
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('DiveLogDialog', message)

class DiveLogWidget(QWidget):
    """Widget for managing dive logs"""
    
    def __init__(self, iface, db_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.db_manager = db_manager
        self.current_site_id = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Site selector
        toolbar.addWidget(QLabel(self.tr("Site:")))
        self.site_combo = QComboBox()
        self.site_combo.currentIndexChanged.connect(self.on_site_changed)
        toolbar.addWidget(self.site_combo)
        toolbar.addSeparator()
        
        # Actions
        self.add_action = toolbar.addAction(self.tr("Add Dive Log"))
        self.add_action.triggered.connect(self.add_dive_log)
        
        self.edit_action = toolbar.addAction(self.tr("Edit"))
        self.edit_action.triggered.connect(self.edit_dive_log)
        self.edit_action.setEnabled(False)
        
        self.delete_action = toolbar.addAction(self.tr("Delete"))
        self.delete_action.triggered.connect(self.delete_dive_log)
        self.delete_action.setEnabled(False)
        
        toolbar.addSeparator()
        
        self.report_action = toolbar.addAction(self.tr("Generate Report"))
        self.report_action.triggered.connect(self.generate_report)
        
        self.batch_report_action = toolbar.addAction(self.tr("Generate All Reports"))
        self.batch_report_action.triggered.connect(self.generate_batch_reports)
        
        toolbar.addSeparator()
        
        # Filters
        toolbar.addWidget(QLabel(self.tr("Year:")))
        self.year_combo = QComboBox()
        self.year_combo.addItem(self.tr("All"))
        current_year = datetime.now().year
        for year in range(current_year, current_year - 10, -1):
            self.year_combo.addItem(str(year))
        self.year_combo.currentTextChanged.connect(self.filter_dives)
        toolbar.addWidget(self.year_combo)
        
        layout.addWidget(toolbar)
        
        # Dive logs table
        self.dives_table = QTableWidget()
        self.dives_table.setColumnCount(11)  # Added Media column
        self.dives_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Dive #"), self.tr("Date"), self.tr("Time"),
            self.tr("Max Depth"), self.tr("Duration"), self.tr("Team Size"),
            self.tr("Media"), self.tr("Visibility"), self.tr("Current"), self.tr("Summary")
        ])
        
        # Hide ID column
        self.dives_table.hideColumn(0)
        
        # Set column widths
        header = self.dives_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.Stretch)  # Summary column (moved due to Media column)
        
        # Selection
        self.dives_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dives_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dives_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.dives_table.cellDoubleClicked.connect(self.edit_dive_log)
        
        layout.addWidget(self.dives_table)
        
        # Statistics
        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)
        
        self.setLayout(layout)
        
        # Load sites
        self.load_sites()
    
    def load_sites(self):
        """Load sites into combo box"""
        self.site_combo.clear()
        self.site_combo.addItem(self.tr("Select Site..."), None)
        
        # Get sites for combo
        try:
            sites = self.db_manager.execute_query(
                "SELECT id, site_name FROM sites WHERE status = 'active' ORDER BY site_name"
            )
            print(f"DEBUG: DiveLog widget - Loading sites, found {len(sites) if sites else 0} sites")
        except Exception as e:
            print(f"ERROR loading sites in DiveLog widget: {e}")
            sites = []
        
        if sites:
            for site in sites:
                if isinstance(site, dict):
                    self.site_combo.addItem(site['site_name'], site['id'])
                else:
                    self.site_combo.addItem(site[1], site[0])
    
    def on_site_changed(self, index):
        """Handle site selection change"""
        self.current_site_id = self.site_combo.currentData()
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh dive logs table"""
        if not self.current_site_id:
            self.dives_table.setRowCount(0)
            self.update_statistics()
            return
        
        # Check if we have the special method for Supabase
        if hasattr(self.db_manager, 'get_dive_logs_for_widget'):
            # Use the Supabase-specific method
            year_filter = self.year_combo.currentText()
            dives = self.db_manager.get_dive_logs_for_widget(self.current_site_id, year_filter)
        else:
            # Use SQL query for SQLite
            # Build query
            query = """
                SELECT d.id, d.dive_number, d.dive_date, 
                       d.dive_start || ' - ' || d.dive_end as time_range,
                       d.max_depth, 
                       CAST((julianday(d.dive_end) - julianday(d.dive_start)) * 24 * 60 AS INTEGER) as duration_min,
                       COUNT(DISTINCT dt.worker_id) as team_size,
                       COUNT(DISTINCT mr.media_id) as media_count,
                       d.visibility, d.current_strength, d.findings_summary
                FROM dive_logs d
                LEFT JOIN dive_team dt ON dt.dive_id = d.id
                LEFT JOIN media_relations mr ON mr.related_id = d.id AND mr.related_type = 'dive_log'
                WHERE d.site_id = ?
            """
            
            params = [self.current_site_id]
            
            # Year filter
            year_filter = self.year_combo.currentText()
            if year_filter != self.tr("All"):
                query += " AND strftime('%Y', d.dive_date) = ?"
                params.append(year_filter)
            
            query += " GROUP BY d.id ORDER BY d.dive_date DESC, d.dive_start DESC"
            
            dives = self.db_manager.execute_query(query, params)
        
        self.dives_table.setRowCount(0)
        
        if dives:
            self.dives_table.setRowCount(len(dives))
            
            for row, dive in enumerate(dives):
                # Handle both dict and tuple
                if isinstance(dive, dict):
                    values = [
                        str(dive.get('id', '')),
                        dive.get('dive_number', ''),
                        dive.get('dive_date', ''),
                        dive.get('time_range', ''),
                        f"{dive.get('max_depth', 0):.1f} m" if dive.get('max_depth') else '',
                        f"{dive.get('duration_min', 0)} min" if dive.get('duration_min') else '',
                        str(dive.get('team_size', 0)),
                        str(dive.get('media_count', 0)),  # Media count column
                        f"{dive.get('visibility', 0):.1f} m" if dive.get('visibility') else '',
                        dive.get('current_strength', ''),
                        dive.get('findings_summary', '')[:100] + '...' if dive.get('findings_summary') else ''
                    ]
                else:
                    values = []
                    for i, val in enumerate(dive):
                        if i == 4 and val:  # max_depth
                            values.append(f"{val:.1f} m")
                        elif i == 5 and val:  # duration
                            values.append(f"{val} min")
                        elif i == 7 and val:  # visibility
                            values.append(f"{val:.1f} m")
                        elif i == 9 and val:  # summary
                            values.append((str(val)[:100] + '...') if len(str(val)) > 100 else str(val))
                        else:
                            values.append(str(val) if val else '')
                
                for col, value in enumerate(values):
                    self.dives_table.setItem(row, col, QTableWidgetItem(value))
        
        self.update_statistics()
    
    def filter_dives(self):
        """Filter dives by year"""
        self.refresh_data()
    
    def update_statistics(self):
        """Update statistics label"""
        if not self.current_site_id:
            self.stats_label.setText("")
            return
        
        # Get statistics
        stats_result = self.db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_dives,
                SUM(CAST((julianday(dive_end) - julianday(dive_start)) * 24 AS REAL)) as total_hours,
                AVG(max_depth) as avg_depth,
                MAX(max_depth) as max_depth
            FROM dive_logs
            WHERE site_id = ?
        """, (self.current_site_id,))
        
        if not stats_result or len(stats_result) == 0:
            self.stats_label.setText(self.tr("No dives recorded for this site"))
            return
            
        stats = stats_result[0]
        
        if isinstance(stats, dict):
            total = stats.get('total_dives', 0)
            hours = stats.get('total_hours', 0) or 0
            avg_depth = stats.get('avg_depth', 0) or 0
            max_depth = stats.get('max_depth', 0) or 0
        else:
            total = stats[0] or 0
            hours = stats[1] or 0
            avg_depth = stats[2] or 0
            max_depth = stats[3] or 0
        
        self.stats_label.setText(
            self.tr(f"Total dives: {total} | Total hours: {hours:.1f} | "
                   f"Average depth: {avg_depth:.1f}m | Maximum depth: {max_depth:.1f}m")
        )
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.dives_table.selectedItems()) > 0
        self.edit_action.setEnabled(has_selection)
        self.delete_action.setEnabled(has_selection)
    
    def add_dive_log(self):
        """Add new dive log"""
        if not self.current_site_id:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Please select a site first")
            )
            return
        
        dlg = DiveLogDialog(self.db_manager, self.current_site_id, parent=self)
        if dlg.exec_():
            dive_data = dlg.get_dive_data()
            
            # Insert dive log
            columns = ', '.join(dive_data.keys())
            placeholders = ', '.join(['?' for _ in dive_data])
            
            dive_id = self.db_manager.execute_update(
                f"INSERT INTO dive_logs ({columns}) VALUES ({placeholders})",
                list(dive_data.values())
            )
            
            if dive_id:
                # Add team members
                for member in dlg.team_members:
                    self.db_manager.execute_update(
                        """INSERT INTO dive_team (dive_id, worker_id, role)
                           VALUES (?, ?, ?)""",
                        (dive_id, member['worker_id'], member['role'])
                    )
                
                # Refresh the dive list
                self.refresh_data()
                
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Dive log added successfully")
                )
    
    def edit_dive_log(self):
        """Edit selected dive log"""
        if not self.dives_table.selectedItems():
            return
        
        row = self.dives_table.currentRow()
        dive_id = int(self.dives_table.item(row, 0).text())
        
        dlg = DiveLogDialog(
            self.db_manager, 
            self.current_site_id, 
            dive_id=dive_id, 
            parent=self
        )
        
        if dlg.exec_():
            # Update dive log
            # (Implementation similar to add but with UPDATE query)
            self.refresh_data()
    
    def delete_dive_log(self):
        """Delete selected dive log"""
        if not self.dives_table.selectedItems():
            return
        
        row = self.dives_table.currentRow()
        dive_id = int(self.dives_table.item(row, 0).text())
        dive_number = self.dives_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr(f"Delete dive log {dive_number}?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Delete team members first
            self.db_manager.execute_update(
                "DELETE FROM dive_team WHERE dive_id = ?",
                (dive_id,)
            )
            
            # Delete dive log
            if self.db_manager.execute_update(
                "DELETE FROM dive_logs WHERE id = ?",
                (dive_id,)
            ):
                self.refresh_data()
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Dive log deleted successfully")
                )
    
    def generate_report(self):
        """Generate dive report with signatures"""
        if not self.dives_table.selectedItems():
            QMessageBox.warning(
                self,
                self.tr("No Selection"),
                self.tr("Please select a dive log to generate report")
            )
            return
        
        row = self.dives_table.currentRow()
        dive_id = int(self.dives_table.item(row, 0).text())
        dive_number = self.dives_table.item(row, 1).text()
        
        # Import the generator
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.report_generator import DiveLogReportGenerator
            
            # Get save location
            from qgis.PyQt.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Save Dive Log Report"),
                f"divelog_{dive_number}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if filename:
                # Generate the report
                generator = DiveLogReportGenerator(self.db_manager)
                if not generator.is_available():
                    QMessageBox.critical(
                        self,
                        self.tr("Missing Dependencies"),
                        self.tr("ReportLab is not installed.\n\nPlease install it with:\npip install reportlab qrcode pillow")
                    )
                    return
                    
                generator.generate_dive_sheet(dive_id, filename)
                
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr(f"Dive log report saved to:\n{filename}")
                )
                
                # Ask if user wants to open the file
                reply = QMessageBox.question(
                    self,
                    self.tr("Open Report"),
                    self.tr("Do you want to open the generated report?"),
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    import subprocess
                    import platform
                    if platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', filename])
                    elif platform.system() == 'Windows':
                        os.startfile(filename)
                    else:  # Linux
                        subprocess.call(['xdg-open', filename])
                        
        except ImportError as e:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr(f"Could not import report generator:\n{str(e)}\n\nPlease ensure reportlab is installed.")
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr(f"Error generating report:\n{str(e)}")
            )
    
    def generate_batch_reports(self):
        """Generate reports for all dive logs"""
        # Get folder location
        from qgis.PyQt.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Folder for Reports"),
            ""
        )
        
        if not folder:
            return
        
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.report_generator import DiveLogReportGenerator
            
            # Get all dive logs
            dives = self.db_manager.execute_query(
                "SELECT id, dive_number FROM dive_logs ORDER BY dive_date"
            )
            
            if not dives:
                QMessageBox.information(
                    self,
                    self.tr("No Data"),
                    self.tr("No dive logs found to generate reports")
                )
                return
            
            # Check if reportlab is available
            generator = DiveLogReportGenerator(self.db_manager)
            if not generator.is_available():
                QMessageBox.critical(
                    self,
                    self.tr("Missing Dependencies"),
                    self.tr("ReportLab is not installed.\n\nPlease install it with:\npip install reportlab qrcode pillow")
                )
                return
                
            # Generate reports
            generated = 0
            
            for dive in dives:
                dive_id = dive['id'] if isinstance(dive, dict) else dive[0]
                dive_number = dive['dive_number'] if isinstance(dive, dict) else dive[1]
                
                filename = os.path.join(folder, f"divelog_{dive_number}.pdf")
                
                try:
                    generator.generate_dive_sheet(dive_id, filename)
                    generated += 1
                except Exception as e:
                    print(f"Error generating report for {dive_number}: {e}")
            
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr(f"Generated {generated} dive log reports in:\n{folder}")
            )
            
            # Ask if user wants to open the folder
            reply = QMessageBox.question(
                self,
                self.tr("Open Folder"),
                self.tr("Do you want to open the reports folder?"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                import subprocess
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', folder])
                elif platform.system() == 'Windows':
                    os.startfile(folder)
                else:  # Linux
                    subprocess.call(['xdg-open', folder])
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr(f"Error generating batch reports:\n{str(e)}")
            )
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('DiveLogWidget', message)