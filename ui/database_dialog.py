# -*- coding: utf-8 -*-
"""
Database creation/opening dialog
"""

import os
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QLabel, QLineEdit, 
                                QFileDialog, QRadioButton, QButtonGroup)
from qgis.PyQt.QtCore import Qt

class DatabaseDialog(QDialog):
    """Dialog for creating or opening a database"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Database Selection"))
        self.setModal(True)
        self.db_path = None
        self.is_new = True
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Radio buttons for new/existing
        self.radio_group = QButtonGroup()
        
        self.new_radio = QRadioButton(self.tr("Create new database"))
        self.new_radio.setChecked(True)
        self.radio_group.addButton(self.new_radio)
        layout.addWidget(self.new_radio)
        
        self.existing_radio = QRadioButton(self.tr("Open existing database"))
        self.radio_group.addButton(self.existing_radio)
        layout.addWidget(self.existing_radio)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel(self.tr("Database file:")))
        
        self.path_edit = QLineEdit()
        file_layout.addWidget(self.path_edit)
        
        self.browse_button = QPushButton(self.tr("Browse..."))
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)
        
        layout.addLayout(file_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton(self.tr("OK"))
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect radio button changes
        self.radio_group.buttonClicked.connect(self.on_radio_changed)
        
    def on_radio_changed(self):
        """Handle radio button changes"""
        self.is_new = self.new_radio.isChecked()
        
    def browse_file(self):
        """Browse for database file"""
        if self.new_radio.isChecked():
            # Save dialog for new database
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Create Database"),
                "",
                self.tr("SpatiaLite Database (*.sqlite *.db)")
            )
        else:
            # Open dialog for existing database
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Open Database"),
                "",
                self.tr("SpatiaLite Database (*.sqlite *.db)")
            )
        
        if file_path:
            self.path_edit.setText(file_path)
            self.db_path = file_path
    
    def get_database_path(self):
        """Get the selected database path"""
        return self.path_edit.text()
    
    def is_new_database(self):
        """Check if creating new database"""
        return self.new_radio.isChecked()
    
    def accept(self):
        """Validate and accept"""
        self.db_path = self.path_edit.text()
        
        if not self.db_path:
            return
        
        if self.existing_radio.isChecked() and not os.path.exists(self.db_path):
            return
        
        super().accept()
    
    def tr(self, message):
        """Get translation"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('DatabaseDialog', message)