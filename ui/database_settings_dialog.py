"""
Database Settings Dialog
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QLineEdit, QPushButton, QGroupBox,
                           QFormLayout, QMessageBox, QFileDialog)
from PyQt5.QtCore import QSettings, pyqtSignal
import os

class DatabaseSettingsDialog(QDialog):
    """Dialog for database connection settings"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings('Lagoi', 'ShipwreckExcavation')
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup dialog UI"""
        self.setWindowTitle("Database Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Database type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Database Type:"))
        
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(['Supabase API (Cloud)', 'SQLite (Local)'])
        self.db_type_combo.currentTextChanged.connect(self.on_db_type_changed)
        type_layout.addWidget(self.db_type_combo)
        
        layout.addLayout(type_layout)
        
        # Supabase settings
        self.pg_group = QGroupBox("Supabase API Settings")
        pg_layout = QFormLayout()
        
        self.pg_host_edit = QLineEdit()
        self.pg_host_edit.setText("db.bqlmbmkffhzayinboanu.supabase.co")
        pg_layout.addRow("Host:", self.pg_host_edit)
        
        self.pg_port_edit = QLineEdit()
        self.pg_port_edit.setText("5432")
        pg_layout.addRow("Port:", self.pg_port_edit)
        
        self.pg_database_edit = QLineEdit()
        self.pg_database_edit.setText("postgres")
        pg_layout.addRow("Database:", self.pg_database_edit)
        
        self.pg_user_edit = QLineEdit()
        self.pg_user_edit.setText("postgres")
        pg_layout.addRow("User:", self.pg_user_edit)
        
        self.pg_password_edit = QLineEdit()
        self.pg_password_edit.setEchoMode(QLineEdit.Password)
        self.pg_password_edit.setText("lagoi2025lagoi")
        pg_layout.addRow("Password:", self.pg_password_edit)
        
        test_pg_btn = QPushButton("Test Connection")
        test_pg_btn.clicked.connect(self.test_pg_connection)
        pg_layout.addRow("", test_pg_btn)
        
        self.pg_group.setLayout(pg_layout)
        layout.addWidget(self.pg_group)
        
        # SQLite settings
        self.sqlite_group = QGroupBox("SQLite Settings")
        sqlite_layout = QFormLayout()
        
        path_layout = QHBoxLayout()
        self.sqlite_path_edit = QLineEdit()
        path_layout.addWidget(self.sqlite_path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_sqlite)
        path_layout.addWidget(browse_btn)
        
        sqlite_layout.addRow("Database Path:", path_layout)
        
        test_sqlite_btn = QPushButton("Test Connection")
        test_sqlite_btn.clicked.connect(self.test_sqlite_connection)
        sqlite_layout.addRow("", test_sqlite_btn)
        
        self.sqlite_group.setLayout(sqlite_layout)
        layout.addWidget(self.sqlite_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def on_db_type_changed(self, text):
        """Handle database type change"""
        is_supabase = 'Supabase' in text
        self.pg_group.setEnabled(is_supabase)
        self.sqlite_group.setEnabled(not is_supabase)
    
    def browse_sqlite(self):
        """Browse for SQLite database"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select SQLite Database",
            "",
            "SQLite Database (*.sqlite *.db);;All Files (*.*)"
        )
        
        if file_path:
            self.sqlite_path_edit.setText(file_path)
    
    def test_pg_connection(self):
        """Test PostgreSQL/Supabase connection"""
        try:
            # Since we're using Supabase API instead of direct connection,
            # test with the Supabase API
            from supabase import create_client, Client
            
            # Get Supabase URL and key
            supabase_url = 'https://bqlmbmkffhzayinboanu.supabase.co'
            supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg'
            
            # Create client
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Test with a simple query
            response = supabase.table('sites').select("id").limit(1).execute()
            
            QMessageBox.information(self, "Success", 
                f"Connected successfully to Supabase!\n\nAPI URL: {supabase_url}\n\nNote: Direct PostgreSQL connection is not available. Using Supabase API instead.")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", 
                f"Failed to connect to Supabase API:\n{str(e)}\n\nPlease check your internet connection.")
    
    def test_sqlite_connection(self):
        """Test SQLite connection"""
        try:
            import sqlite3
            
            if not os.path.exists(self.sqlite_path_edit.text()):
                raise Exception("Database file not found")
            
            conn = sqlite3.connect(self.sqlite_path_edit.text())
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sites")
            count = cur.fetchone()[0]
            conn.close()
            
            QMessageBox.information(self, "Success", 
                f"Connected successfully!\n\nFound {count} sites")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", str(e))
    
    def load_settings(self):
        """Load saved settings"""
        db_type = self.settings.value('database/type', 'supabase')
        
        if db_type == 'supabase' or db_type == 'postgresql':
            self.db_type_combo.setCurrentIndex(0)  # Supabase API
        else:
            self.db_type_combo.setCurrentIndex(1)  # SQLite
        
        # Load PostgreSQL settings
        self.pg_host_edit.setText(
            self.settings.value('postgresql/host', 'db.bqlmbmkffhzayinboanu.supabase.co'))
        self.pg_port_edit.setText(
            self.settings.value('postgresql/port', '5432'))
        self.pg_database_edit.setText(
            self.settings.value('postgresql/database', 'postgres'))
        self.pg_user_edit.setText(
            self.settings.value('postgresql/user', 'postgres'))
        
        # Load SQLite settings
        self.sqlite_path_edit.setText(
            self.settings.value('sqlite/path', ''))
    
    def save_settings(self):
        """Save settings"""
        if 'Supabase' in self.db_type_combo.currentText():
            self.settings.setValue('database/type', 'supabase')
            
            # Save PostgreSQL settings
            self.settings.setValue('postgresql/host', self.pg_host_edit.text())
            self.settings.setValue('postgresql/port', self.pg_port_edit.text())
            self.settings.setValue('postgresql/database', self.pg_database_edit.text())
            self.settings.setValue('postgresql/user', self.pg_user_edit.text())
            
            # Build and save connection string
            conn_string = (
                f"postgresql://{self.pg_user_edit.text()}:"
                f"{self.pg_password_edit.text()}@"
                f"{self.pg_host_edit.text()}:"
                f"{self.pg_port_edit.text()}/"
                f"{self.pg_database_edit.text()}"
            )
            os.environ['SUPABASE_DB_URL'] = conn_string
            
        else:
            self.settings.setValue('database/type', 'sqlite')
            self.settings.setValue('sqlite/path', self.sqlite_path_edit.text())
        
        self.settings_changed.emit()
        self.accept()
