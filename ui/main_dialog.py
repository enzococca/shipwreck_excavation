# -*- coding: utf-8 -*-
"""
Main dialog for Shipwreck Excavation Management
"""

import os
import sys

from qgis.PyQt.QtCore import Qt, QSettings, pyqtSignal
from qgis.PyQt.QtWidgets import (QDialog, QTabWidget, QVBoxLayout, 
                                QMessageBox, QFileDialog, QToolBar, QAction)
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsFeature, QgsGeometry, QgsPointXY, Qgis

# Add parent directory to path for imports
plugin_dir = os.path.dirname(os.path.dirname(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

# Import widgets using absolute imports
from ui.finds_widget import FindsWidget
from ui.media_widget import MediaWidget
from ui.divelog_widget import DiveLogWidget
from ui.workers_widget import WorkersWidget
from ui.costs_widget import CostsWidget
from ui.site_widget import SiteWidget
from ui.sync_status_widget import SyncStatusWidget

# Database factory for PostgreSQL/SQLite support
from database.database_factory import DatabaseFactory

class ShipwreckMainDialog(QDialog):
    """Main dialog for the plugin"""
    
    closingPlugin = pyqtSignal()
    
    def __init__(self, iface, db_manager, settings, parent=None):
        """Constructor"""
        super(ShipwreckMainDialog, self).__init__(parent)
        
        self.iface = iface
        self.db_manager = db_manager
        self.settings = settings
        self.sync_manager = None
        
        # Use database factory for PostgreSQL support
        if hasattr(self.db_manager, '__class__') and 'PostgreSQL' not in str(self.db_manager.__class__):
            self.db_manager = DatabaseFactory.create_database_manager()
        
        # Set window properties
        self.setWindowTitle("Shipwreck Excavation Management")
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint |
                           Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.resize(1000, 700)
        
        # Initialize UI
        self.init_ui()
        
        # Load settings
        self.load_settings()
        
    
    def create_toolbar(self):
        """Create toolbar with settings"""
        toolbar = QToolBar()
        
        # Database settings action
        settings_action = QAction(QIcon(), "Database Settings", self)
        settings_action.triggered.connect(self.open_database_settings)
        toolbar.addAction(settings_action)
        
        # Sync status action  
        sync_action = QAction(QIcon(), "Sync Status", self)
        sync_action.triggered.connect(self.show_sync_status)
        toolbar.addAction(sync_action)
        
        return toolbar
    
    def open_database_settings(self):
        """Open database settings dialog"""
        from ui.database_settings_dialog import DatabaseSettingsDialog
        dialog = DatabaseSettingsDialog(self)
        dialog.settings_changed.connect(self.on_database_settings_changed)
        dialog.exec_()
    
    def on_database_settings_changed(self):
        """Handle database settings change"""
        QMessageBox.information(self, "Settings Changed", 
            "Database settings updated. Please restart the plugin.")
    
    def show_sync_status(self):
        """Show sync status"""
        if hasattr(self, 'sync_status_widget') and self.sync_status_widget:
            self.sync_status_widget.update_status()
        else:
            QMessageBox.information(self, "Sync Status", "Sync is not configured for this session.")
    
    def init_ui(self):
        """Initialize the user interface"""
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create widgets for each tab
        self.site_widget = SiteWidget(self.iface, self.db_manager, self)
        self.finds_widget = FindsWidget(self.iface, self.db_manager, self)
        self.media_widget = MediaWidget(self.iface, self.db_manager, self)
        self.divelog_widget = DiveLogWidget(self.iface, self.db_manager, self)
        self.workers_widget = WorkersWidget(self.iface, self.db_manager, self)
        self.costs_widget = CostsWidget(self.iface, self.db_manager, self)
        
        # Create statistics widget
        from ui.statistics_widget import StatisticsWidget
        self.statistics_widget = StatisticsWidget(self.db_manager, parent=self)
        
        # Add tabs
        self.tab_widget.addTab(self.site_widget, self.tr("Sites"))
        self.tab_widget.addTab(self.finds_widget, self.tr("Finds"))
        self.tab_widget.addTab(self.media_widget, self.tr("Media"))
        self.tab_widget.addTab(self.statistics_widget, self.tr("Statistics"))
        self.tab_widget.addTab(self.divelog_widget, self.tr("Dive Logs"))
        self.tab_widget.addTab(self.workers_widget, self.tr("Workers"))
        self.tab_widget.addTab(self.costs_widget, self.tr("Costs"))
        
        # Create status bar with sync status
        if self.sync_manager:
            self.sync_status_widget = SyncStatusWidget(self.sync_manager, self)
            self.sync_status_widget.configure_clicked.connect(self.open_sync_config)
            self.sync_status_widget.sync_now_clicked.connect(self.sync_now)
        else:
            self.sync_status_widget = None
        
        # Set layout
        layout = QVBoxLayout()
        layout.addWidget(self.create_toolbar())
        layout.addWidget(self.tab_widget)
        
        # Add sync status widget at bottom
        if self.sync_status_widget:
            layout.addWidget(self.sync_status_widget)
        
        self.setLayout(layout)
        
        # Connect signals
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Connect site updates to refresh other widgets
        self.site_widget.sites_updated.connect(self.on_sites_updated)
        
        # Set window size
        self.resize(1000, 700)
        
    def on_tab_changed(self, index):
        """Handle tab change"""
        # Refresh data in the current tab
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()
    
    def on_sites_updated(self):
        """Handle site updates - refresh site lists in all widgets"""
        # Refresh sites in all widgets that have load_sites method
        widgets = [self.finds_widget, self.media_widget, self.divelog_widget, 
                  self.workers_widget, self.costs_widget, self.statistics_widget]
        for widget in widgets:
            if hasattr(widget, 'load_sites'):
                widget.load_sites()
            elif hasattr(widget, 'refresh_data'):
                widget.refresh_data()
    
    def load_settings(self):
        """Load dialog settings"""
        # Restore window geometry
        geometry = self.settings.value("MainDialog/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore last tab
        last_tab = self.settings.value("MainDialog/lastTab", 0, type=int)
        self.tab_widget.setCurrentIndex(last_tab)
    
    def save_settings(self):
        """Save dialog settings"""
        # Save window geometry
        self.settings.setValue("MainDialog/geometry", self.saveGeometry())
        
        # Save current tab
        self.settings.setValue("MainDialog/lastTab", self.tab_widget.currentIndex())
    
    def closeEvent(self, event):
        """Handle close event"""
        self.save_settings()
        self.closingPlugin.emit()
        event.accept()
    
    def set_sync_manager(self, sync_manager):
        """Set sync manager after dialog creation"""
        self.sync_manager = sync_manager
        
        # Update sync status widget if it exists
        if hasattr(self, 'sync_status_widget') and self.sync_status_widget:
            self.sync_status_widget.sync_manager = sync_manager
            # Reconnect signals
            if sync_manager:
                sync_manager.sync_started.connect(self.sync_status_widget.on_sync_started)
                sync_manager.sync_finished.connect(self.sync_status_widget.on_sync_finished)
                sync_manager.sync_progress.connect(self.sync_status_widget.on_sync_progress)
            self.sync_status_widget.update_status()
    
    def open_sync_config(self):
        """Open sync configuration dialog"""
        from ui.cloud_sync_dialog import CloudSyncDialog
        
        dlg = CloudSyncDialog(
            self,
            self.sync_manager,
            self.db_manager.db_path
        )
        dlg.exec_()
    
    def sync_now(self):
        """Start sync now"""
        if self.sync_manager:
            self.sync_manager.start_sync()
    
    def tr(self, message):
        """Get translation"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('ShipwreckMainDialog', message)