# -*- coding: utf-8 -*-
"""
Simplified plugin for testing
"""

import os
import sys
from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QDialog, QVBoxLayout, QLabel
from qgis.core import Qgis

class SimpleShipwreckPlugin:
    """Simplified plugin for testing"""
    
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = '&Shipwreck Excavation'
        
        # Add plugin directory to Python path
        if self.plugin_dir not in sys.path:
            sys.path.append(self.plugin_dir)
            
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""
        icon_path = os.path.join(self.plugin_dir, 'icons', 'shipwreck.png')
        if not os.path.exists(icon_path):
            icon_path = ''
            
        action = QAction(
            QIcon(icon_path),
            'Shipwreck Excavation Management',
            self.iface.mainWindow()
        )
        action.triggered.connect(self.run)
        
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI"""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
            
    def run(self):
        """Run method that performs the work"""
        # Create a simple dialog
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle("Shipwreck Excavation - Test")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        label = QLabel("Plugin loaded successfully!\n\nTesting imports...")
        layout.addWidget(label)
        
        # Test imports
        import_results = []
        
        try:
            from database.db_manager import DatabaseManager
            import_results.append("✓ DatabaseManager")
        except Exception as e:
            import_results.append(f"✗ DatabaseManager: {str(e)}")
            
        try:
            from ui.main_dialog import ShipwreckMainDialog
            import_results.append("✓ ShipwreckMainDialog")
        except Exception as e:
            import_results.append(f"✗ ShipwreckMainDialog: {str(e)}")
            
        results_label = QLabel("\n".join(import_results))
        layout.addWidget(results_label)
        
        dialog.setLayout(layout)
        dialog.exec_()