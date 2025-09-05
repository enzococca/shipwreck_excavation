# -*- coding: utf-8 -*-
"""Workers management widget"""

from qgis.PyQt.QtCore import Qt, QDate, pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QToolBar,
                                QLineEdit, QLabel, QMessageBox, QHeaderView,
                                QFormLayout, QDialog, QDialogButtonBox,
                                QTextEdit, QCheckBox, QComboBox, QTabWidget,
                                QCalendarWidget, QDoubleSpinBox)
from qgis.PyQt.QtGui import QIcon
from datetime import datetime, date

class WorkerDialog(QDialog):
    """Dialog for adding/editing workers"""
    
    def __init__(self, db_manager, worker_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.worker_id = worker_id
        self.setWindowTitle(self.tr("Worker Details"))
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.init_ui()
        
        if worker_id:
            self.load_worker_data()
        else:
            self.generate_worker_code()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Worker code
        self.worker_code_edit = QLineEdit()
        form_layout.addRow(self.tr("Worker Code:"), self.worker_code_edit)
        
        # Full name
        self.name_edit = QLineEdit()
        form_layout.addRow(self.tr("Full Name:"), self.name_edit)
        
        # Role
        self.role_combo = QComboBox()
        self.role_combo.setEditable(True)
        self.role_combo.addItems([
            "Lead Archaeologist", "Archaeologist", "Dive Supervisor",
            "Diver", "Photographer", "Conservator", "Technician",
            "Field Assistant", "Boat Operator"
        ])
        form_layout.addRow(self.tr("Role:"), self.role_combo)
        
        # Qualification
        self.qualification_edit = QLineEdit()
        self.qualification_edit.setPlaceholderText("e.g., MA Archaeology, BSc Marine Biology")
        form_layout.addRow(self.tr("Qualification:"), self.qualification_edit)
        
        # Dive certification
        self.dive_cert_combo = QComboBox()
        self.dive_cert_combo.setEditable(True)
        self.dive_cert_combo.addItems([
            "", "Open Water", "Advanced Open Water", "Rescue Diver",
            "Divemaster", "Instructor", "Technical Diver", "Commercial Diver"
        ])
        form_layout.addRow(self.tr("Dive Certification:"), self.dive_cert_combo)
        
        # Contact info
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+62...")
        form_layout.addRow(self.tr("Phone:"), self.phone_edit)
        
        self.email_edit = QLineEdit()
        form_layout.addRow(self.tr("Email:"), self.email_edit)
        
        self.telegram_edit = QLineEdit()
        self.telegram_edit.setPlaceholderText("@username")
        form_layout.addRow(self.tr("Telegram:"), self.telegram_edit)
        
        # Emergency contact
        self.emergency_edit = QTextEdit()
        self.emergency_edit.setMaximumHeight(60)
        self.emergency_edit.setPlaceholderText("Name, relationship, phone number")
        form_layout.addRow(self.tr("Emergency Contact:"), self.emergency_edit)
        
        # Active status
        self.active_check = QCheckBox(self.tr("Active"))
        self.active_check.setChecked(True)
        form_layout.addRow("", self.active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def generate_worker_code(self):
        """Generate next worker code"""
        result = self.db_manager.execute_query(
            "SELECT worker_code FROM workers ORDER BY id DESC LIMIT 1"
        )
        
        if result:
            # Handle both tuple and Row object formats
            if isinstance(result[0], tuple):
                last_code = result[0][0]
            else:
                # sqlite3.Row object - access by column name
                last_code = result[0]['worker_code']
            try:
                parts = last_code.split('-')
                if len(parts) > 1:
                    num = int(parts[-1]) + 1
                    new_code = f"W-{num:04d}"
                else:
                    new_code = "W-0001"
            except:
                new_code = "W-0001"
        else:
            new_code = "W-0001"
        
        self.worker_code_edit.setText(new_code)
    
    def load_worker_data(self):
        """Load existing worker data"""
        if hasattr(self.db_manager, 'get_workers'):
            # For Supabase
            workers = self.db_manager.get_workers()
            worker = next((w for w in workers if w['id'] == self.worker_id), None)
            if worker:
                data = worker
            else:
                return
        else:
            # For SQLite
            result = self.db_manager.execute_query(
                "SELECT * FROM workers WHERE id = ?",
                (self.worker_id,)
            )
            if not result:
                return
            data = result[0]
        
        # Populate fields
        self.worker_code_edit.setText(data.get('worker_code', ''))
        self.name_edit.setText(data.get('full_name', ''))
        
        # Set role
        role = data.get('role', '')
        index = self.role_combo.findText(role, Qt.MatchFixedString)
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        else:
            self.role_combo.setEditText(role)
        
        self.qualification_edit.setText(data.get('qualification', ''))
        
        # Set dive certification
        dive_cert = data.get('dive_certification', '')
        index = self.dive_cert_combo.findText(dive_cert, Qt.MatchFixedString)
        if index >= 0:
            self.dive_cert_combo.setCurrentIndex(index)
        else:
            self.dive_cert_combo.setEditText(dive_cert)
        
        self.phone_edit.setText(data.get('phone', ''))
        self.email_edit.setText(data.get('email', ''))
        self.telegram_edit.setText(data.get('telegram_username', ''))
        self.emergency_edit.setText(data.get('emergency_contact', ''))
        self.active_check.setChecked(data.get('is_active', data.get('active', False)))
    
    def get_worker_data(self):
        """Get worker data from form"""
        return {
            'worker_code': self.worker_code_edit.text(),
            'full_name': self.name_edit.text(),
            'role': self.role_combo.currentText(),
            'qualification': self.qualification_edit.text(),
            'dive_certification': self.dive_cert_combo.currentText(),
            'phone': self.phone_edit.text(),
            'email': self.email_edit.text(),
            'telegram_username': self.telegram_edit.text(),
            'emergency_contact': self.emergency_edit.toPlainText(),
            'is_active': self.active_check.isChecked()
        }
    
    def accept(self):
        """Validate and save"""
        if not self.worker_code_edit.text() or not self.name_edit.text():
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Worker code and name are required")
            )
            return
        
        super().accept()
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('WorkerDialog', message)

class WorkSessionDialog(QDialog):
    """Dialog for recording work sessions"""
    
    def __init__(self, db_manager, worker_id, site_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.worker_id = worker_id
        self.site_id = site_id
        self.setWindowTitle(self.tr("Work Session"))
        self.setModal(True)
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # Work date
        self.date_edit = QCalendarWidget()
        self.date_edit.setSelectedDate(QDate.currentDate())
        form_layout.addRow(self.tr("Date:"), self.date_edit)
        
        # Work type
        self.work_type_combo = QComboBox()
        self.work_type_combo.addItems([
            "Diving", "Processing", "Documentation", "Conservation",
            "Research", "Transport", "Other"
        ])
        form_layout.addRow(self.tr("Work Type:"), self.work_type_combo)
        
        # Hours
        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.5, 24)
        self.hours_spin.setSingleStep(0.5)
        self.hours_spin.setValue(8.0)
        form_layout.addRow(self.tr("Hours Worked:"), self.hours_spin)
        
        # Rate
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setMaximum(999999)
        self.rate_spin.setPrefix("IDR ")
        form_layout.addRow(self.tr("Rate per Hour:"), self.rate_spin)
        
        # Total (calculated)
        self.total_label = QLabel("IDR 0")
        form_layout.addRow(self.tr("Total:"), self.total_label)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        form_layout.addRow(self.tr("Notes:"), self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # Connect signals
        self.hours_spin.valueChanged.connect(self.calculate_total)
        self.rate_spin.valueChanged.connect(self.calculate_total)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def calculate_total(self):
        """Calculate total payment"""
        total = self.hours_spin.value() * self.rate_spin.value()
        self.total_label.setText(f"IDR {total:,.0f}")
    
    def get_session_data(self):
        """Get session data"""
        return {
            'worker_id': self.worker_id,
            'site_id': self.site_id,
            'work_date': self.date_edit.selectedDate().toString('yyyy-MM-dd'),
            'work_type': self.work_type_combo.currentText(),
            'hours_worked': self.hours_spin.value(),
            'rate_per_hour': self.rate_spin.value(),
            'total_payment': self.hours_spin.value() * self.rate_spin.value(),
            'payment_status': 'pending',
            'notes': self.notes_edit.toPlainText()
        }
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('WorkSessionDialog', message)

class WorkersWidget(QWidget):
    """Widget for managing workers"""
    
    def __init__(self, iface, db_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.db_manager = db_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Workers tab
        self.workers_tab = self.create_workers_tab()
        self.tab_widget.addTab(self.workers_tab, self.tr("Workers"))
        
        # Work sessions tab
        self.sessions_tab = self.create_sessions_tab()
        self.tab_widget.addTab(self.sessions_tab, self.tr("Work Sessions"))
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
        # Load initial data after UI is created
        self.load_workers()
        self.load_sites()
        
    def refresh_data(self):
        """Refresh data when tab is activated"""
        self.load_workers()
        self.load_sites()
        self.refresh_sessions()
    
    def create_workers_tab(self):
        """Create workers management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Actions
        self.add_worker_action = toolbar.addAction(self.tr("Add Worker"))
        self.add_worker_action.triggered.connect(self.add_worker)
        
        self.edit_worker_action = toolbar.addAction(self.tr("Edit"))
        self.edit_worker_action.triggered.connect(self.edit_worker)
        self.edit_worker_action.setEnabled(False)
        
        self.delete_worker_action = toolbar.addAction(self.tr("Delete"))
        self.delete_worker_action.triggered.connect(self.delete_worker)
        self.delete_worker_action.setEnabled(False)
        
        toolbar.addSeparator()
        
        # Search
        toolbar.addWidget(QLabel(self.tr("Search:")))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Name or code..."))
        self.search_edit.textChanged.connect(self.filter_workers)
        toolbar.addWidget(self.search_edit)
        
        # Active filter
        self.active_only_check = QCheckBox(self.tr("Active only"))
        self.active_only_check.setChecked(True)
        self.active_only_check.stateChanged.connect(self.filter_workers)
        toolbar.addWidget(self.active_only_check)
        
        layout.addWidget(toolbar)
        
        # Workers table
        self.workers_table = QTableWidget()
        self.workers_table.setColumnCount(8)
        self.workers_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Code"), self.tr("Name"), self.tr("Role"),
            self.tr("Phone"), self.tr("Email"), self.tr("Dive Cert"), self.tr("Active")
        ])
        
        # Hide ID column
        self.workers_table.hideColumn(0)
        
        # Set column widths
        header = self.workers_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Name column
        
        # Selection
        self.workers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.workers_table.setSelectionMode(QTableWidget.SingleSelection)
        self.workers_table.itemSelectionChanged.connect(self.on_worker_selection_changed)
        self.workers_table.cellDoubleClicked.connect(self.edit_worker)
        
        layout.addWidget(self.workers_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_sessions_tab(self):
        """Create work sessions tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Selectors
        toolbar.addWidget(QLabel(self.tr("Site:")))
        self.site_combo = QComboBox()
        self.site_combo.currentIndexChanged.connect(self.refresh_sessions)
        toolbar.addWidget(self.site_combo)
        
        toolbar.addWidget(QLabel(self.tr("Worker:")))
        self.worker_combo = QComboBox()
        self.worker_combo.currentIndexChanged.connect(self.refresh_sessions)
        toolbar.addWidget(self.worker_combo)
        
        toolbar.addSeparator()
        
        # Actions
        self.add_session_action = toolbar.addAction(self.tr("Add Session"))
        self.add_session_action.triggered.connect(self.add_session)
        
        self.mark_paid_action = toolbar.addAction(self.tr("Mark as Paid"))
        self.mark_paid_action.triggered.connect(self.mark_paid)
        self.mark_paid_action.setEnabled(False)
        
        toolbar.addSeparator()
        
        # Month filter
        toolbar.addWidget(QLabel(self.tr("Month:")))
        self.month_combo = QComboBox()
        self.month_combo.addItem(self.tr("All"))
        # Add last 12 months
        current_date = date.today()
        for i in range(12):
            month_date = date(current_date.year, current_date.month, 1)
            month_date = month_date.replace(month=((current_date.month - i - 1) % 12) + 1)
            if i >= current_date.month:
                month_date = month_date.replace(year=current_date.year - 1)
            self.month_combo.addItem(month_date.strftime("%B %Y"), month_date.strftime("%Y-%m"))
        self.month_combo.currentIndexChanged.connect(self.refresh_sessions)
        toolbar.addWidget(self.month_combo)
        
        layout.addWidget(toolbar)
        
        # Sessions table
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(9)
        self.sessions_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Date"), self.tr("Worker"), self.tr("Site"),
            self.tr("Type"), self.tr("Hours"), self.tr("Rate"), self.tr("Total"),
            self.tr("Status")
        ])
        
        # Hide ID column
        self.sessions_table.hideColumn(0)
        
        # Set column widths
        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Selection
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sessions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sessions_table.itemSelectionChanged.connect(self.on_session_selection_changed)
        
        layout.addWidget(self.sessions_table)
        
        # Summary
        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)
        
        widget.setLayout(layout)
        return widget
    
    def refresh_data(self):
        """Refresh all data"""
        self.load_workers()
        self.load_sites()
        self.refresh_sessions()
    
    def load_workers(self):
        """Load workers list"""
        # Clear the table first
        self.workers_table.setRowCount(0)
        self.worker_combo.clear()
        self.worker_combo.addItem(self.tr("All Workers"), None)
        
        # Get workers from database
        try:
            if hasattr(self.db_manager, 'get_workers'):
                # Use Supabase method if available
                workers = self.db_manager.get_workers()
                print(f"DEBUG: Loading workers via get_workers(), found {len(workers) if workers else 0} workers")
            else:
                workers = self.db_manager.execute_query(
                    "SELECT * FROM workers ORDER BY full_name"
                )
                print(f"DEBUG: Loading workers via SQL, found {len(workers) if workers else 0} workers")
        except Exception as e:
            print(f"ERROR loading workers: {e}")
            workers = []
        
        # Debug print the first worker if exists
        if workers and len(workers) > 0:
            print(f"DEBUG: First worker type: {type(workers[0])}")
            if hasattr(workers[0], 'keys'):
                print(f"DEBUG: Worker keys: {list(workers[0].keys())}")
        
        if workers:
            for worker in workers:
                # sqlite3.Row objects act like dictionaries but need different access
                try:
                    # Try dictionary-style access for sqlite3.Row
                    worker_id = worker['id']
                    worker_code = worker['worker_code'] or ''
                    full_name = worker['full_name'] or ''
                    role = worker['role'] or ''
                    phone = worker['phone'] or ''
                    email = worker['email'] or ''
                    dive_cert = worker['dive_certification'] or ''
                    active = worker.get('is_active', worker.get('active', False))
                    
                    # Add to combo if active
                    if active:
                        self.worker_combo.addItem(full_name, worker_id)
                    
                    # Add to table
                    row = self.workers_table.rowCount()
                    self.workers_table.insertRow(row)
                    
                    self.workers_table.setItem(row, 0, QTableWidgetItem(str(worker_id)))
                    self.workers_table.setItem(row, 1, QTableWidgetItem(worker_code))
                    self.workers_table.setItem(row, 2, QTableWidgetItem(full_name))
                    self.workers_table.setItem(row, 3, QTableWidgetItem(role))
                    self.workers_table.setItem(row, 4, QTableWidgetItem(phone))
                    self.workers_table.setItem(row, 5, QTableWidgetItem(email))
                    self.workers_table.setItem(row, 6, QTableWidgetItem(dive_cert))
                    self.workers_table.setItem(row, 7, QTableWidgetItem("✓" if active else ""))
                    
                except Exception as e:
                    print(f"DEBUG: Error loading worker: {e}")
                    print(f"DEBUG: Worker type: {type(worker)}")
                    if hasattr(worker, '__dict__'):
                        print(f"DEBUG: Worker dict: {worker.__dict__}")
                    continue
        
        self.filter_workers()
    
    def load_sites(self):
        """Load sites list"""
        self.site_combo.clear()
        self.site_combo.addItem(self.tr("All Sites"), None)
        
        sites = self.db_manager.execute_query(
            "SELECT id, site_name FROM sites WHERE status = 'active' ORDER BY site_name"
        )
        
        if sites:
            for site in sites:
                if isinstance(site, dict):
                    self.site_combo.addItem(site['site_name'], site['id'])
                else:
                    self.site_combo.addItem(site[1], site[0])
    
    def filter_workers(self):
        """Filter workers table"""
        search_text = self.search_edit.text().lower()
        active_only = self.active_only_check.isChecked()
        
        for row in range(self.workers_table.rowCount()):
            show_row = True
            
            # Text filter
            if search_text:
                code = self.workers_table.item(row, 1).text().lower()
                name = self.workers_table.item(row, 2).text().lower()
                if search_text not in code and search_text not in name:
                    show_row = False
            
            # Active filter
            if active_only:
                active = self.workers_table.item(row, 7).text() == "✓"
                if not active:
                    show_row = False
            
            self.workers_table.setRowHidden(row, not show_row)
    
    def refresh_sessions(self):
        """Refresh work sessions"""
        # Build query
        query = """
            SELECT ws.id, ws.work_date, w.full_name, s.site_name,
                   ws.work_type, ws.hours_worked, ws.rate_per_hour,
                   ws.total_payment, ws.payment_status
            FROM work_session ws
            JOIN workers w ON w.id = ws.worker_id
            JOIN sites s ON s.id = ws.site_id
            WHERE 1=1
        """
        params = []
        
        # Site filter
        site_id = self.site_combo.currentData()
        if site_id:
            query += " AND ws.site_id = ?"
            params.append(site_id)
        
        # Worker filter
        worker_id = self.worker_combo.currentData()
        if worker_id:
            query += " AND ws.worker_id = ?"
            params.append(worker_id)
        
        # Month filter
        month_filter = self.month_combo.currentData()
        if month_filter and self.month_combo.currentIndex() > 0:
            query += " AND strftime('%Y-%m', ws.work_date) = ?"
            params.append(month_filter)
        
        query += " ORDER BY ws.work_date DESC"
        
        sessions = self.db_manager.execute_query(query, params)
        
        self.sessions_table.setRowCount(0)
        total_hours = 0
        total_payment = 0
        
        if sessions:
            for session in sessions:
                row = self.sessions_table.rowCount()
                self.sessions_table.insertRow(row)
                
                if isinstance(session, dict):
                    values = [
                        str(session['id']),
                        session['work_date'],
                        session['full_name'],
                        session['site_name'],
                        session['work_type'],
                        f"{session['hours_worked']:.1f}",
                        f"IDR {session['rate_per_hour']:,.0f}",
                        f"IDR {session['total_payment']:,.0f}",
                        session['payment_status']
                    ]
                    
                    total_hours += session['hours_worked']
                    total_payment += session['total_payment']
                else:
                    values = [str(v) if v else '' for v in session]
                    if len(session) > 5:
                        total_hours += session[5] or 0
                    if len(session) > 7:
                        total_payment += session[7] or 0
                
                for col, value in enumerate(values):
                    self.sessions_table.setItem(row, col, QTableWidgetItem(value))
        
        # Update summary
        self.summary_label.setText(
            self.tr(f"Total: {total_hours:.1f} hours | IDR {total_payment:,.0f}")
        )
    
    def on_worker_selection_changed(self):
        """Handle worker selection change"""
        has_selection = len(self.workers_table.selectedItems()) > 0
        self.edit_worker_action.setEnabled(has_selection)
        self.delete_worker_action.setEnabled(has_selection)
    
    def on_session_selection_changed(self):
        """Handle session selection change"""
        has_selection = len(self.sessions_table.selectedItems()) > 0
        if has_selection:
            row = self.sessions_table.currentRow()
            status = self.sessions_table.item(row, 8).text()
            self.mark_paid_action.setEnabled(status == 'pending')
        else:
            self.mark_paid_action.setEnabled(False)
    
    def add_worker(self):
        """Add new worker"""
        dlg = WorkerDialog(self.db_manager, parent=self)
        if dlg.exec_():
            data = dlg.get_worker_data()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            result = self.db_manager.execute_update(
                f"INSERT INTO workers ({columns}) VALUES ({placeholders})",
                list(data.values())
            )
            
            if result:
                print(f"DEBUG: Worker added successfully, refreshing list")
                # Force refresh
                self.workers_table.clearContents()
                self.workers_table.setRowCount(0)
                self.load_workers()
                
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Worker added successfully")
                )
            else:
                QMessageBox.warning(
                    self,
                    self.tr("Error"),
                    self.tr("Failed to add worker")
                )
    
    def edit_worker(self):
        """Edit selected worker"""
        if not self.workers_table.selectedItems():
            return
        
        row = self.workers_table.currentRow()
        worker_id = int(self.workers_table.item(row, 0).text())
        
        dlg = WorkerDialog(self.db_manager, worker_id=worker_id, parent=self)
        if dlg.exec_():
            # Update worker
            data = dlg.get_worker_data()
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [worker_id]
            
            if self.db_manager.execute_update(
                f"UPDATE workers SET {set_clause} WHERE id = ?",
                values
            ):
                self.load_workers()
    
    def delete_worker(self):
        """Delete selected worker"""
        if not self.workers_table.selectedItems():
            return
        
        row = self.workers_table.currentRow()
        worker_id = int(self.workers_table.item(row, 0).text())
        worker_name = self.workers_table.item(row, 2).text()
        
        # Check if worker has sessions (work_session table might not exist yet)
        try:
            sessions_result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM work_session WHERE worker_id = ?",
                (worker_id,)
            )
            
            # Handle both empty result and different data formats
            session_count = 0
            if sessions_result and len(sessions_result) > 0:
                if isinstance(sessions_result[0], dict):
                    session_count = sessions_result[0].get('count', 0)
                elif isinstance(sessions_result[0], (tuple, list)) and len(sessions_result[0]) > 0:
                    session_count = sessions_result[0][0]
        except Exception as e:
            print(f"DEBUG: Error checking work_session (table might not exist): {e}")
            session_count = 0  # Assume no sessions if table doesn't exist
        
        if session_count > 0:
            reply = QMessageBox.question(
                self,
                self.tr("Deactivate Worker"),
                self.tr(f"Worker '{worker_name}' has work sessions. Deactivate instead of delete?"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # For Supabase, need to use is_active field
                if hasattr(self.db_manager, 'supabase'):
                    result = self.db_manager.execute_update(
                        "UPDATE workers SET is_active = false WHERE id = ?",
                        (worker_id,)
                    )
                else:
                    result = self.db_manager.execute_update(
                        "UPDATE workers SET active = 0 WHERE id = ?",
                        (worker_id,)
                    )
                if result:
                    QMessageBox.information(self, self.tr("Success"), self.tr("Worker deactivated"))
                self.load_workers()
        else:
            reply = QMessageBox.question(
                self,
                self.tr("Confirm Delete"),
                self.tr(f"Delete worker '{worker_name}'?"),
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.db_manager.execute_update(
                    "DELETE FROM workers WHERE id = ?",
                    (worker_id,)
                ):
                    self.load_workers()
    
    def add_session(self):
        """Add work session"""
        worker_id = self.worker_combo.currentData()
        site_id = self.site_combo.currentData()
        
        if not worker_id or not site_id:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Please select both worker and site")
            )
            return
        
        dlg = WorkSessionDialog(self.db_manager, worker_id, site_id, parent=self)
        if dlg.exec_():
            data = dlg.get_session_data()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            if self.db_manager.execute_update(
                f"INSERT INTO work_session ({columns}) VALUES ({placeholders})",
                list(data.values())
            ):
                self.refresh_sessions()
    
    def mark_paid(self):
        """Mark session as paid"""
        if not self.sessions_table.selectedItems():
            return
        
        row = self.sessions_table.currentRow()
        session_id = int(self.sessions_table.item(row, 0).text())
        
        if self.db_manager.execute_update(
            "UPDATE work_session SET payment_status = 'paid' WHERE id = ?",
            (session_id,)
        ):
            self.refresh_sessions()
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('WorkersWidget', message)