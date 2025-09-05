# -*- coding: utf-8 -*-
"""
Cloud Sync Configuration Dialog
"""

import os
from pathlib import Path
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QLineEdit, QPushButton, QComboBox, QCheckBox,
                                 QGroupBox, QSpinBox, QFileDialog, QMessageBox,
                                 QProgressBar, QTextEdit, QRadioButton, QButtonGroup,
                                 QProgressDialog, QApplication)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon

class CloudSyncDialog(QDialog):
    """Dialog for cloud sync configuration"""
    
    sync_configured = pyqtSignal(str, str)  # provider, path
    
    def __init__(self, parent=None, sync_manager=None, db_path=None):
        super().__init__(parent)
        self.sync_manager = sync_manager
        self.db_path = db_path
        self.setWindowTitle("Configurazione Sincronizzazione Cloud")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Provider selection
        provider_group = QGroupBox("Provider Cloud Storage")
        provider_layout = QVBoxLayout()
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "Dropbox",
            "Google Drive", 
            "OneDrive",
            "Cartella di rete",
            "Cartella locale (test)"
        ])
        provider_layout.addWidget(QLabel("Seleziona provider:"))
        provider_layout.addWidget(self.provider_combo)
        
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)
        
        # Path configuration
        path_group = QGroupBox("Percorso Sincronizzazione")
        path_layout = QVBoxLayout()
        
        path_input_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.browse_btn = QPushButton("Sfoglia...")
        self.browse_btn.clicked.connect(self.browse_path)
        
        path_input_layout.addWidget(self.path_edit)
        path_input_layout.addWidget(self.browse_btn)
        
        path_layout.addWidget(QLabel("Percorso cartella cloud:"))
        path_layout.addLayout(path_input_layout)
        
        # Show example paths
        self.example_label = QLabel()
        self.example_label.setWordWrap(True)
        self.example_label.setStyleSheet("color: gray; font-style: italic;")
        self.update_example_path()
        path_layout.addWidget(self.example_label)
        
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # Sync options
        options_group = QGroupBox("Opzioni Sincronizzazione")
        options_layout = QVBoxLayout()
        
        self.auto_sync_check = QCheckBox("Sincronizzazione automatica")
        self.auto_sync_check.setChecked(True)
        options_layout.addWidget(self.auto_sync_check)
        
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Intervallo sincronizzazione:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(60, 3600)
        self.interval_spin.setValue(300)
        self.interval_spin.setSuffix(" secondi")
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        options_layout.addLayout(interval_layout)
        
        # Conflict resolution
        conflict_layout = QVBoxLayout()
        conflict_layout.addWidget(QLabel("Risoluzione conflitti:"))
        
        self.conflict_group = QButtonGroup()
        self.ask_radio = QRadioButton("Chiedi sempre")
        self.local_radio = QRadioButton("Mantieni versione locale")
        self.remote_radio = QRadioButton("Mantieni versione remota")
        self.newest_radio = QRadioButton("Mantieni più recente")
        
        self.ask_radio.setChecked(True)
        
        self.conflict_group.addButton(self.ask_radio, 0)
        self.conflict_group.addButton(self.local_radio, 1)
        self.conflict_group.addButton(self.remote_radio, 2)
        self.conflict_group.addButton(self.newest_radio, 3)
        
        conflict_layout.addWidget(self.ask_radio)
        conflict_layout.addWidget(self.local_radio)
        conflict_layout.addWidget(self.remote_radio)
        conflict_layout.addWidget(self.newest_radio)
        
        options_layout.addLayout(conflict_layout)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Status
        status_group = QGroupBox("Stato Sincronizzazione")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        status_layout.addWidget(self.status_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Clone section
        clone_group = QGroupBox("Clona da Cloud")
        clone_layout = QVBoxLayout()
        
        clone_info = QLabel("Usa questa opzione per creare una copia locale di un progetto esistente nel cloud.")
        clone_info.setWordWrap(True)
        clone_layout.addWidget(clone_info)
        
        self.clone_btn = QPushButton("Clona Progetto da Cloud...")
        self.clone_btn.clicked.connect(self.clone_from_cloud)
        self.clone_btn.setIcon(QIcon.fromTheme("folder-download"))
        clone_layout.addWidget(self.clone_btn)
        
        clone_group.setLayout(clone_layout)
        layout.addWidget(clone_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connessione")
        self.test_btn.clicked.connect(self.test_connection)
        
        self.sync_now_btn = QPushButton("Sincronizza Ora")
        self.sync_now_btn.clicked.connect(self.sync_now)
        self.sync_now_btn.setEnabled(False)
        
        self.save_btn = QPushButton("Salva")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.sync_now_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connect signals
        self.provider_combo.currentTextChanged.connect(self.update_example_path)
        self.auto_sync_check.toggled.connect(self.interval_spin.setEnabled)
        
        if self.sync_manager:
            self.sync_manager.sync_progress.connect(self.update_progress)
            self.sync_manager.sync_finished.connect(self.on_sync_finished)
    
    def update_example_path(self):
        """Update example path based on provider"""
        provider = self.provider_combo.currentText()
        
        examples = {
            "Dropbox": "/Users/[username]/Dropbox/lagoi2025/",
            "Google Drive": "/Users/[username]/Google Drive/lagoi2025/",
            "OneDrive": "/Users/[username]/OneDrive/lagoi2025/",
            "Cartella di rete": "//server/share/lagoi2025/",
            "Cartella locale (test)": "/Users/[username]/Documents/lagoi2025_sync/"
        }
        
        example = examples.get(provider, "")
        self.example_label.setText(f"Esempio: {example}")
    
    def browse_path(self):
        """Browse for sync path"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella di sincronizzazione",
            self.path_edit.text() or os.path.expanduser("~")
        )
        
        if path:
            self.path_edit.setText(path)
    
    def test_connection(self):
        """Test cloud connection"""
        provider = self.provider_combo.currentText()
        path = self.path_edit.text()
        
        if not path:
            QMessageBox.warning(self, "Attenzione", "Inserisci il percorso di sincronizzazione")
            return
        
        self.status_text.clear()
        self.status_text.append(f"Test connessione {provider}...")
        
        # Check if path exists and is writable
        try:
            test_path = Path(path)
            if not test_path.exists():
                test_path.mkdir(parents=True, exist_ok=True)
            
            # Try to write test file
            test_file = test_path / ".sync_test"
            test_file.write_text("test")
            test_file.unlink()
            
            self.status_text.append("✓ Connessione riuscita!")
            self.status_text.append("✓ Permessi di scrittura OK")
            self.sync_now_btn.setEnabled(True)
            
            # Check available space
            stat = os.statvfs(path)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            self.status_text.append(f"✓ Spazio disponibile: {free_gb:.1f} GB")
            
        except Exception as e:
            self.status_text.append(f"✗ Errore: {str(e)}")
            self.sync_now_btn.setEnabled(False)
    
    def sync_now(self):
        """Start sync now"""
        if not self.sync_manager:
            return
        
        self.progress_bar.setVisible(True)
        self.sync_now_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        
        # Configure and start sync
        provider = self.provider_combo.currentText()
        path = self.path_edit.text()
        
        if self.db_path:
            local_path = os.path.dirname(self.db_path)
            self.sync_manager.configure_sync(provider, path, local_path)
            self.sync_manager.start_sync()
    
    def update_progress(self, message, percentage):
        """Update sync progress"""
        self.status_text.append(message)
        self.progress_bar.setValue(percentage)
    
    def on_sync_finished(self, success, message):
        """Handle sync completion"""
        self.progress_bar.setVisible(False)
        self.sync_now_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        if success:
            self.status_text.append(f"✓ {message}")
        else:
            self.status_text.append(f"✗ {message}")
    
    def save_settings(self):
        """Save sync settings"""
        if not self.sync_manager:
            return
        
        provider = self.provider_combo.currentText()
        path = self.path_edit.text()
        
        if not path:
            QMessageBox.warning(self, "Attenzione", "Inserisci il percorso di sincronizzazione")
            return
        
        # Update sync manager settings
        self.sync_manager.sync_provider = provider
        self.sync_manager.sync_path = path
        self.sync_manager.sync_enabled = True
        self.sync_manager.auto_sync_enabled = self.auto_sync_check.isChecked()
        self.sync_manager.sync_interval = self.interval_spin.value()
        
        # Set conflict resolution
        conflict_modes = ['ask', 'local', 'remote', 'newest']
        self.sync_manager.conflict_resolution = conflict_modes[self.conflict_group.checkedId()]
        
        # Configure sync with local path
        if self.db_path:
            local_path = os.path.dirname(self.db_path)
            self.sync_manager.configure_sync(provider, path, local_path)
        
        self.sync_manager.save_settings()
        
        QMessageBox.information(self, "Successo", "Impostazioni salvate correttamente")
        self.sync_configured.emit(provider, path)
        self.accept()
    
    def load_settings(self):
        """Load existing settings"""
        if not self.sync_manager:
            return
        
        # Load provider
        providers = ["Dropbox", "Google Drive", "OneDrive", "Cartella di rete", "Cartella locale (test)"]
        if self.sync_manager.sync_provider in [p.lower().replace(" ", "") for p in providers]:
            for i, p in enumerate(providers):
                if p.lower().replace(" ", "") == self.sync_manager.sync_provider:
                    self.provider_combo.setCurrentIndex(i)
                    break
        
        # Load path
        self.path_edit.setText(self.sync_manager.sync_path)
        
        # Load options
        self.auto_sync_check.setChecked(self.sync_manager.auto_sync_enabled)
        self.interval_spin.setValue(self.sync_manager.sync_interval)
        
        # Load conflict resolution
        conflict_modes = {'ask': 0, 'local': 1, 'remote': 2, 'newest': 3}
        mode_id = conflict_modes.get(self.sync_manager.conflict_resolution, 0)
        self.conflict_group.button(mode_id).setChecked(True)
        
        # Update status
        if self.sync_manager.sync_enabled:
            status = self.sync_manager.get_sync_status()
            self.status_text.append(f"Provider: {status['provider']}")
            self.status_text.append(f"Percorso: {status['path']}")
            if 'last_sync' in status:
                self.status_text.append(f"Ultima sincronizzazione: {status['last_sync'].strftime('%Y-%m-%d %H:%M')}")
            self.sync_now_btn.setEnabled(True)
    
    def clone_from_cloud(self):
        """Clone project from cloud"""
        # Get cloud path
        cloud_path = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella progetto nel cloud",
            self.path_edit.text() or os.path.expanduser("~")
        )
        
        if not cloud_path:
            return
        
        # Check if it contains a database
        cloud_path_obj = Path(cloud_path)
        db_files = list(cloud_path_obj.glob('*.sqlite')) + list(cloud_path_obj.glob('*.db'))
        
        if not db_files:
            QMessageBox.warning(
                self,
                "Nessun Database",
                "La cartella selezionata non contiene un database SQLite"
            )
            return
        
        # Get local destination
        local_path = QFileDialog.getExistingDirectory(
            self,
            "Seleziona dove salvare il progetto localmente",
            os.path.expanduser("~/Documents")
        )
        
        if not local_path:
            return
        
        # Create progress dialog
        progress = QProgressDialog(
            "Clonazione in corso...",
            "Annulla",
            0, 100,
            self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(True)
        progress.show()
        
        # Clone with progress callback
        def update_progress(msg, percentage):
            progress.setLabelText(msg)
            progress.setValue(percentage)
            QApplication.processEvents()
            return not progress.wasCanceled()
        
        # Perform clone
        success, db_path, error = self.sync_manager.clone_from_cloud(
            cloud_path,
            local_path,
            update_progress
        )
        
        progress.close()
        
        if success:
            reply = QMessageBox.question(
                self,
                "Clonazione Completata",
                f"Progetto clonato con successo!\n\n"
                f"Database: {os.path.basename(db_path)}\n\n"
                f"Vuoi aprire il database clonato ora?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Emit signal to open database
                from qgis.PyQt.QtCore import QTimer
                QTimer.singleShot(100, lambda: self.open_cloned_database(db_path))
                self.accept()
        else:
            QMessageBox.critical(
                self,
                "Errore Clonazione",
                f"Impossibile clonare il progetto:\n{error}"
            )
    
    def open_cloned_database(self, db_path):
        """Open the cloned database"""
        # This will be handled by the main plugin
        if hasattr(self.parent(), 'db_manager'):
            db_manager = self.parent().db_manager
            if db_manager.connect(db_path):
                db_manager.add_layers_to_qgis()
                
                # Configure sync automatically
                cloud_path = os.path.dirname(db_path)
                self.sync_manager.configure_sync(
                    self.provider_combo.currentText(),
                    str(Path(db_path).parent),
                    cloud_path
                )