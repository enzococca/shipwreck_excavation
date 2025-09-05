# -*- coding: utf-8 -*-
"""
Sync Status Widget
Shows cloud sync status in the main UI
"""

from qgis.PyQt.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                                 QToolButton, QMenu, QAction)
from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QPixmap, QPainter, QColor

class SyncStatusWidget(QWidget):
    """Widget showing sync status"""
    
    # Signals
    configure_clicked = pyqtSignal()
    sync_now_clicked = pyqtSignal()
    
    def __init__(self, sync_manager=None, parent=None):
        super().__init__(parent)
        self.sync_manager = sync_manager
        self.init_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        # Connect to sync manager signals
        if self.sync_manager:
            self.sync_manager.sync_started.connect(self.on_sync_started)
            self.sync_manager.sync_finished.connect(self.on_sync_finished)
            self.sync_manager.sync_progress.connect(self.on_sync_progress)
    
    def init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        
        # Status icon
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(16, 16)
        layout.addWidget(self.status_icon)
        
        # Status label
        self.status_label = QLabel("Sync: Not configured")
        self.status_label.setStyleSheet("QLabel { color: gray; }")
        layout.addWidget(self.status_label)
        
        # Sync button
        self.sync_btn = QToolButton()
        self.sync_btn.setText("↻")
        self.sync_btn.setToolTip("Sincronizza ora")
        self.sync_btn.clicked.connect(self.sync_now_clicked)
        self.sync_btn.setEnabled(False)
        layout.addWidget(self.sync_btn)
        
        # Menu button
        self.menu_btn = QToolButton()
        self.menu_btn.setText("⋮")
        self.menu_btn.setPopupMode(QToolButton.InstantPopup)
        
        menu = QMenu()
        menu.addAction("Configura sincronizzazione", self.configure_clicked)
        menu.addAction("Sincronizza ora", self.sync_now_clicked)
        menu.addSeparator()
        
        self.auto_sync_action = menu.addAction("Sincronizzazione automatica")
        self.auto_sync_action.setCheckable(True)
        self.auto_sync_action.triggered.connect(self.toggle_auto_sync)
        
        self.menu_btn.setMenu(menu)
        layout.addWidget(self.menu_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Initial update
        self.update_status()
    
    def create_status_icon(self, color):
        """Create colored status icon"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        return pixmap
    
    def update_status(self):
        """Update sync status display"""
        if not self.sync_manager:
            self.status_icon.setPixmap(self.create_status_icon("gray"))
            self.status_label.setText("Sync: Not configured")
            self.status_label.setStyleSheet("QLabel { color: gray; }")
            self.sync_btn.setEnabled(False)
            return
        
        status = self.sync_manager.get_sync_status()
        
        if not status['enabled']:
            self.status_icon.setPixmap(self.create_status_icon("gray"))
            self.status_label.setText("Sync: Not configured")
            self.status_label.setStyleSheet("QLabel { color: gray; }")
            self.sync_btn.setEnabled(False)
        elif status['syncing']:
            self.status_icon.setPixmap(self.create_status_icon("orange"))
            self.status_label.setText("Sincronizzazione in corso...")
            self.status_label.setStyleSheet("QLabel { color: orange; }")
            self.sync_btn.setEnabled(False)
        else:
            self.status_icon.setPixmap(self.create_status_icon("green"))
            
            # Show last sync time
            if 'last_sync' in status and status['last_sync']:
                time_diff = (datetime.now() - status['last_sync']).total_seconds()
                
                if time_diff < 60:
                    time_str = "ora"
                elif time_diff < 3600:
                    time_str = f"{int(time_diff/60)} min fa"
                elif time_diff < 86400:
                    time_str = f"{int(time_diff/3600)} ore fa"
                else:
                    time_str = f"{int(time_diff/86400)} giorni fa"
                
                self.status_label.setText(f"Sync: {time_str}")
            else:
                self.status_label.setText("Sync: Mai sincronizzato")
            
            self.status_label.setStyleSheet("QLabel { color: green; }")
            self.sync_btn.setEnabled(True)
        
        # Update auto sync checkbox
        self.auto_sync_action.setChecked(status.get('auto_sync', False))
    
    def on_sync_started(self):
        """Handle sync started"""
        self.status_icon.setPixmap(self.create_status_icon("orange"))
        self.status_label.setText("Sincronizzazione in corso...")
        self.status_label.setStyleSheet("QLabel { color: orange; }")
        self.sync_btn.setEnabled(False)
    
    def on_sync_progress(self, message, percentage):
        """Handle sync progress"""
        self.status_label.setText(f"Sync: {percentage}%")
    
    def on_sync_finished(self, success, message):
        """Handle sync finished"""
        self.update_status()
    
    def toggle_auto_sync(self, checked):
        """Toggle auto sync"""
        if self.sync_manager:
            self.sync_manager.auto_sync_enabled = checked
            if checked:
                self.sync_manager.start_auto_sync()
            else:
                self.sync_manager.stop_auto_sync()
            self.sync_manager.save_settings()

# Import datetime for time calculations
from datetime import datetime