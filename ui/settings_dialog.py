# -*- coding: utf-8 -*-
"""
Settings dialog for the plugin
"""

from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QLabel, QLineEdit, 
                                QComboBox, QSpinBox, QGroupBox,
                                QFormLayout, QFileDialog)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis

class SettingsDialog(QDialog):
    """Settings dialog"""
    
    def __init__(self, db_manager, settings, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.settings = settings
        
        self.setWindowTitle(self.tr("Settings"))
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # General settings
        general_group = QGroupBox(self.tr("General"))
        general_layout = QFormLayout()
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Bahasa Indonesia", "id")
        general_layout.addRow(self.tr("Language:"), self.language_combo)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # Telegram settings
        telegram_group = QGroupBox(self.tr("Telegram"))
        telegram_layout = QFormLayout()
        
        # Bot token
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)
        telegram_layout.addRow(self.tr("Bot Token:"), self.token_edit)
        
        # Sync interval
        self.sync_interval = QSpinBox()
        self.sync_interval.setMinimum(60)
        self.sync_interval.setMaximum(3600)
        self.sync_interval.setSuffix(" " + self.tr("seconds"))
        self.sync_interval.setSingleStep(60)
        telegram_layout.addRow(self.tr("Sync Interval:"), self.sync_interval)
        
        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)
        
        # Storage settings
        storage_group = QGroupBox(self.tr("Storage"))
        storage_layout = QFormLayout()
        
        # Add explanation label
        explanation_label = QLabel(self.tr("Each user must set their own local Google Drive path.\n"
                                          "This path is stored locally and not shared with other users."))
        explanation_label.setWordWrap(True)
        explanation_label.setStyleSheet("QLabel { color: #666; font-style: italic; margin-bottom: 10px; }")
        storage_layout.addRow(explanation_label)
        
        # Media path
        media_layout = QHBoxLayout()
        self.media_path_edit = QLineEdit()
        self.media_path_edit.setPlaceholderText(self.tr("e.g., /path/to/GoogleDrive/lagoi-database/"))
        media_layout.addWidget(self.media_path_edit)
        
        browse_button = QPushButton(self.tr("Browse..."))
        browse_button.clicked.connect(self.browse_media_path)
        media_layout.addWidget(browse_button)
        
        storage_layout.addRow(self.tr("Your Local Media Path:"), media_layout)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
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
    
    def load_settings(self):
        """Load current settings"""
        # Language
        lang = self.db_manager.get_setting('language') or 'en'
        index = self.language_combo.findData(lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        
        # Telegram token
        token = self.db_manager.get_setting('telegram_bot_token') or ''
        self.token_edit.setText(token)
        
        # Sync interval
        interval = int(self.db_manager.get_setting('sync_interval') or 300)
        self.sync_interval.setValue(interval)
        
        # Media path - try to load from QSettings
        media_path = self.db_manager.get_setting('media_base_path') or ''
        QgsMessageLog.logMessage(f"Settings Dialog - Loaded media path: {media_path}", "Settings", Qgis.Info)
        self.media_path_edit.setText(media_path)
    
    def browse_media_path(self):
        """Browse for media storage path"""
        path = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Media Storage Directory"),
            self.media_path_edit.text()
        )
        
        if path:
            self.media_path_edit.setText(path)
    
    def accept(self):
        """Save settings and close"""
        # Log what we're saving
        media_path = self.media_path_edit.text()
        QgsMessageLog.logMessage(f"Settings Dialog - Saving media path: {media_path}", "Settings", Qgis.Info)
        
        # Save to database
        self.db_manager.set_setting('language', self.language_combo.currentData())
        self.db_manager.set_setting('telegram_bot_token', self.token_edit.text())
        self.db_manager.set_setting('sync_interval', str(self.sync_interval.value()))
        self.db_manager.set_setting('media_storage_path', media_path)
        
        # Save to QSettings directly as backup
        self.settings.setValue('language', self.language_combo.currentData())
        self.settings.setValue('media_base_path', media_path)
        self.settings.setValue('media_storage_path', media_path)
        self.settings.sync()
        
        # Also save using db_manager's QSettings instance
        if hasattr(self.db_manager, 'settings'):
            self.db_manager.settings.setValue('media_base_path', media_path)
            self.db_manager.settings.setValue('media_storage_path', media_path)
            self.db_manager.settings.sync()
            QgsMessageLog.logMessage(f"Also saved to db_manager.settings", "Settings", Qgis.Info)
        
        # Log verification
        test_value1 = self.settings.value('media_base_path')
        test_value2 = self.db_manager.settings.value('media_base_path') if hasattr(self.db_manager, 'settings') else None
        QgsMessageLog.logMessage(f"Settings Dialog - Verification self.settings: {test_value1}", "Settings", Qgis.Info)
        QgsMessageLog.logMessage(f"Settings Dialog - Verification db_manager.settings: {test_value2}", "Settings", Qgis.Info)
        
        super().accept()
    
    def tr(self, message):
        """Get translation"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('SettingsDialog', message)