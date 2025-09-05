# -*- coding: utf-8 -*-
"""
Test minimal plugin to check import issues
"""

import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import Qgis

class TestShipwreckPlugin:
    """Minimal test plugin"""
    
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = '&Shipwreck Test'
        
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""
        icon_path = os.path.join(self.plugin_dir, 'icons', 'shipwreck.png')
        if not os.path.exists(icon_path):
            icon_path = ''
            
        action = QAction(
            QIcon(icon_path),
            'Test Shipwreck Plugin',
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
        QMessageBox.information(
            self.iface.mainWindow(),
            "Success",
            "Test plugin loaded successfully!\n\nNow checking imports..."
        )
        
        # Test imports
        try:
            from database.db_manager import DatabaseManager
            QMessageBox.information(
                self.iface.mainWindow(),
                "Import Test",
                "DatabaseManager imported successfully!"
            )
        except ImportError as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Import Error",
                f"Failed to import DatabaseManager:\n{str(e)}"
            )