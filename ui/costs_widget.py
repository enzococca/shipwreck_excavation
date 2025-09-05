# -*- coding: utf-8 -*-
"""Costs management widget"""

from qgis.PyQt.QtCore import Qt, QDate, pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QToolBar,
                                QLineEdit, QLabel, QMessageBox, QHeaderView,
                                QFormLayout, QDialog, QDialogButtonBox,
                                QTextEdit, QDateEdit, QComboBox, QTabWidget,
                                QDoubleSpinBox, QGroupBox)
from qgis.PyQt.QtGui import QIcon, QFont
# Chart imports commented out - can be enabled if QtChart is available
# from qgis.PyQt.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from datetime import datetime, date
import json

class ExpenseDialog(QDialog):
    """Dialog for adding/editing expenses"""
    
    def __init__(self, db_manager, site_id, expense_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.site_id = site_id
        self.expense_id = expense_id
        self.setWindowTitle(self.tr("Expense Entry"))
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.init_ui()
        
        if expense_id:
            self.load_expense_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow(self.tr("Date:"), self.date_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            "Equipment", "Boat Rental", "Fuel", "Accommodation",
            "Food & Supplies", "Transportation", "Conservation Materials",
            "Documentation", "Permits", "Insurance", "Other"
        ])
        form_layout.addRow(self.tr("Category:"), self.category_combo)
        
        # Description
        self.description_edit = QLineEdit()
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        
        # Supplier
        self.supplier_edit = QLineEdit()
        form_layout.addRow(self.tr("Supplier:"), self.supplier_edit)
        
        # Amount
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999)
        self.amount_spin.setPrefix("IDR ")
        form_layout.addRow(self.tr("Amount:"), self.amount_spin)
        
        # Payment method
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "Bank Transfer", "Credit Card", "Other"])
        form_layout.addRow(self.tr("Payment Method:"), self.payment_combo)
        
        # Receipt number
        self.receipt_edit = QLineEdit()
        form_layout.addRow(self.tr("Receipt #:"), self.receipt_edit)
        
        # Approved by
        self.approved_edit = QLineEdit()
        form_layout.addRow(self.tr("Approved By:"), self.approved_edit)
        
        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        form_layout.addRow(self.tr("Notes:"), self.notes_edit)
        
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
    
    def load_expense_data(self):
        """Load existing expense data"""
        # Get table name based on database type
        table_name = "costs" if hasattr(self.db_manager, 'supabase') else "expenses"
        expense = self.db_manager.execute_query(
            f"SELECT * FROM {table_name} WHERE id = ?",
            (self.expense_id,)
        )
        
        if expense:
            data = expense[0]
            # Populate fields based on data
    
    def get_expense_data(self):
        """Get expense data from form"""
        return {
            'site_id': self.site_id,
            'expense_date': self.date_edit.date().toString('yyyy-MM-dd'),
            'category': self.category_combo.currentText(),
            'description': self.description_edit.text(),
            'supplier': self.supplier_edit.text(),
            'amount': self.amount_spin.value(),
            'currency': 'IDR',
            'payment_method': self.payment_combo.currentText(),
            'receipt_number': self.receipt_edit.text(),
            'approved_by': self.approved_edit.text(),
            'notes': self.notes_edit.toPlainText()
        }
    
    def accept(self):
        """Validate and save"""
        if not self.description_edit.text() or self.amount_spin.value() == 0:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Description and amount are required")
            )
            return
        
        super().accept()
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('ExpenseDialog', message)

class CostsWidget(QWidget):
    """Widget for managing excavation costs"""
    
    def __init__(self, iface, db_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.db_manager = db_manager
        self.current_site_id = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Expenses tab
        self.expenses_tab = self.create_expenses_tab()
        self.tab_widget.addTab(self.expenses_tab, self.tr("Expenses"))
        
        # Summary tab
        self.summary_tab = self.create_summary_tab()
        self.tab_widget.addTab(self.summary_tab, self.tr("Summary & Reports"))
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
        # Load sites
        self.load_sites()
    
    def create_expenses_tab(self):
        """Create expenses management tab"""
        widget = QWidget()
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
        self.add_expense_action = toolbar.addAction(self.tr("Add Expense"))
        self.add_expense_action.triggered.connect(self.add_expense)
        
        self.edit_expense_action = toolbar.addAction(self.tr("Edit"))
        self.edit_expense_action.triggered.connect(self.edit_expense)
        self.edit_expense_action.setEnabled(False)
        
        self.delete_expense_action = toolbar.addAction(self.tr("Delete"))
        self.delete_expense_action.triggered.connect(self.delete_expense)
        self.delete_expense_action.setEnabled(False)
        
        toolbar.addSeparator()
        
        # Filters
        toolbar.addWidget(QLabel(self.tr("Category:")))
        self.category_filter = QComboBox()
        self.category_filter.addItem(self.tr("All Categories"))
        self.category_filter.currentTextChanged.connect(self.filter_expenses)
        toolbar.addWidget(self.category_filter)
        
        toolbar.addWidget(QLabel(self.tr("Month:")))
        self.month_filter = QComboBox()
        self.month_filter.addItem(self.tr("All"))
        # Add last 12 months
        current_date = date.today()
        for i in range(12):
            month_date = date(current_date.year, current_date.month, 1)
            month_date = month_date.replace(month=((current_date.month - i - 1) % 12) + 1)
            if i >= current_date.month:
                month_date = month_date.replace(year=current_date.year - 1)
            self.month_filter.addItem(month_date.strftime("%B %Y"), month_date.strftime("%Y-%m"))
        self.month_filter.currentIndexChanged.connect(self.filter_expenses)
        toolbar.addWidget(self.month_filter)
        
        layout.addWidget(toolbar)
        
        # Expenses table
        self.expenses_table = QTableWidget()
        self.expenses_table.setColumnCount(9)
        self.expenses_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Date"), self.tr("Category"), 
            self.tr("Description"), self.tr("Supplier"), self.tr("Amount"),
            self.tr("Payment"), self.tr("Receipt"), self.tr("Approved")
        ])
        
        # Hide ID column
        self.expenses_table.hideColumn(0)
        
        # Set column widths
        header = self.expenses_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Description
        
        # Selection
        self.expenses_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.expenses_table.setSelectionMode(QTableWidget.SingleSelection)
        self.expenses_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.expenses_table.cellDoubleClicked.connect(self.edit_expense)
        
        layout.addWidget(self.expenses_table)
        
        # Total label
        self.total_label = QLabel()
        font = QFont()
        font.setBold(True)
        self.total_label.setFont(font)
        layout.addWidget(self.total_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_summary_tab(self):
        """Create summary and reports tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel(self.tr("Period:")))
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            self.tr("This Month"), self.tr("Last 3 Months"),
            self.tr("Last 6 Months"), self.tr("This Year"),
            self.tr("All Time")
        ])
        self.period_combo.currentIndexChanged.connect(self.update_summary)
        controls_layout.addWidget(self.period_combo)
        
        controls_layout.addStretch()
        
        self.export_btn = QPushButton(self.tr("Export Report"))
        self.export_btn.clicked.connect(self.export_report)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)
        
        # Summary groups
        summary_layout = QHBoxLayout()
        
        # Cost breakdown
        breakdown_group = QGroupBox(self.tr("Cost Breakdown"))
        breakdown_layout = QVBoxLayout()
        
        self.breakdown_table = QTableWidget()
        self.breakdown_table.setColumnCount(3)
        self.breakdown_table.setHorizontalHeaderLabels([
            self.tr("Category"), self.tr("Amount"), self.tr("Percentage")
        ])
        header = self.breakdown_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        breakdown_layout.addWidget(self.breakdown_table)
        
        breakdown_group.setLayout(breakdown_layout)
        summary_layout.addWidget(breakdown_group)
        
        # Monthly totals
        monthly_group = QGroupBox(self.tr("Monthly Summary"))
        monthly_layout = QVBoxLayout()
        
        self.monthly_table = QTableWidget()
        self.monthly_table.setColumnCount(3)
        self.monthly_table.setHorizontalHeaderLabels([
            self.tr("Month"), self.tr("Expenses"), self.tr("Labor")
        ])
        header = self.monthly_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        monthly_layout.addWidget(self.monthly_table)
        
        monthly_group.setLayout(monthly_layout)
        summary_layout.addWidget(monthly_group)
        
        layout.addLayout(summary_layout)
        
        # Chart view (placeholder)
        self.chart_view = QLabel(self.tr("Charts will be displayed here"))
        self.chart_view.setMinimumHeight(200)
        self.chart_view.setStyleSheet("border: 1px solid #ccc; background: #f0f0f0;")
        self.chart_view.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.chart_view)
        
        # Grand total
        self.grand_total_label = QLabel()
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.grand_total_label.setFont(font)
        self.grand_total_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.grand_total_label)
        
        widget.setLayout(layout)
        return widget
    
    def load_sites(self):
        """Load sites into combo box"""
        self.site_combo.clear()
        self.site_combo.addItem(self.tr("Select Site..."), None)
        
        sites = self.db_manager.execute_query(
            "SELECT id, site_name FROM sites ORDER BY site_name"
        )
        
        if sites:
            for site in sites:
                if isinstance(site, dict):
                    self.site_combo.addItem(site['site_name'], site['id'])
                else:
                    self.site_combo.addItem(site[1], site[0])
    
    def on_site_changed(self, index):
        """Handle site selection change"""
        self.current_site_id = self.site_combo.currentData()
        self.refresh_expenses()
        self.update_summary()
        self.load_categories()
    
    def load_categories(self):
        """Load categories for filter"""
        if not self.current_site_id:
            return
        
        # Get table name based on database type
        table_name = "costs" if hasattr(self.db_manager, 'supabase') else "expenses"
        
        categories = self.db_manager.execute_query(
            f"SELECT DISTINCT category FROM {table_name} WHERE site_id = ? ORDER BY category",
            (self.current_site_id,)
        )
        
        self.category_filter.clear()
        self.category_filter.addItem(self.tr("All Categories"))
        
        if categories:
            for cat in categories:
                if isinstance(cat, dict):
                    self.category_filter.addItem(cat['category'])
                else:
                    self.category_filter.addItem(cat[0])
    
    def refresh_expenses(self):
        """Refresh expenses table"""
        if not self.current_site_id:
            self.expenses_table.setRowCount(0)
            self.total_label.setText("")
            return
        
        # Build query - check if using costs or expenses table
        if hasattr(self.db_manager, 'supabase'):
            # Supabase uses 'costs' table
            query = """
                SELECT id, cost_date as expense_date, category, description, 
                       created_by as supplier, amount, currency as payment_method, 
                       notes as receipt_number, created_by as approved_by
                FROM costs
                WHERE site_id = ?
            """
        else:
            # SQLite uses 'expenses' table
            query = """
                SELECT id, expense_date, category, description, supplier,
                       amount, payment_method, receipt_number, approved_by
                FROM expenses
                WHERE site_id = ?
            """
        params = [self.current_site_id]
        
        # Category filter
        category = self.category_filter.currentText()
        if category != self.tr("All Categories"):
            query += " AND category = ?"
            params.append(category)
        
        # Month filter
        month_data = self.month_filter.currentData()
        if month_data and self.month_filter.currentIndex() > 0:
            # For Supabase, we need to filter by date range
            query += " AND expense_date >= ? AND expense_date < ?"
            # Create first and last day of month
            year, month = month_data.split('-')
            first_day = f"{year}-{month}-01"
            # Calculate last day of month
            if month == '12':
                next_month = f"{int(year)+1}-01-01"
            else:
                next_month = f"{year}-{int(month)+1:02d}-01"
            params.extend([first_day, next_month])
        
        query += " ORDER BY expense_date DESC"
        
        print(f"DEBUG Costs: Query: {query}")
        print(f"DEBUG Costs: Params: {params}")
        expenses = self.db_manager.execute_query(query, params)
        print(f"DEBUG Costs: Found {len(expenses) if expenses else 0} expenses")
        
        self.expenses_table.setRowCount(0)
        total = 0
        
        if expenses:
            for expense in expenses:
                row = self.expenses_table.rowCount()
                self.expenses_table.insertRow(row)
                
                if isinstance(expense, dict):
                    # Handle different field names between costs (Supabase) and expenses (SQLite)
                    values = [
                        str(expense['id']),
                        expense.get('expense_date', expense.get('cost_date', '')),
                        expense['category'],
                        expense['description'],
                        expense.get('supplier', expense.get('created_by', '')),
                        f"IDR {expense['amount']:,.0f}",
                        expense.get('payment_method', expense.get('currency', 'IDR')),
                        expense.get('receipt_number', expense.get('notes', '')),
                        expense.get('approved_by', expense.get('created_by', ''))
                    ]
                    total += expense['amount']
                else:
                    values = [str(v) if v else '' for v in expense]
                    if len(expense) > 5:
                        values[5] = f"IDR {expense[5]:,.0f}"
                        total += expense[5]
                
                for col, value in enumerate(values):
                    self.expenses_table.setItem(row, col, QTableWidgetItem(value))
        
        self.total_label.setText(self.tr(f"Total: IDR {total:,.0f}"))
    
    def filter_expenses(self):
        """Filter expenses based on selections"""
        self.refresh_expenses()
    
    def update_summary(self):
        """Update summary tab"""
        if not self.current_site_id:
            return
        
        # Get period
        period = self.period_combo.currentIndex()
        date_filter = ""
        
        if period == 0:  # This month
            if hasattr(self.db_manager, 'supabase'):
                date_filter = f"AND cost_date >= date_trunc('month', CURRENT_DATE)"
            else:
                date_filter = f"AND expense_date >= date('now', 'start of month')"
        elif period == 1:  # Last 3 months
            if hasattr(self.db_manager, 'supabase'):
                date_filter = f"AND cost_date >= CURRENT_DATE - INTERVAL '3 months'"
            else:
                date_filter = f"AND expense_date >= date('now', '-3 months')"
        elif period == 2:  # Last 6 months
            if hasattr(self.db_manager, 'supabase'):
                date_filter = f"AND cost_date >= CURRENT_DATE - INTERVAL '6 months'"
            else:
                date_filter = f"AND expense_date >= date('now', '-6 months')"
        elif period == 3:  # This year
            if hasattr(self.db_manager, 'supabase'):
                date_filter = f"AND cost_date >= date_trunc('year', CURRENT_DATE)"
            else:
                date_filter = f"AND expense_date >= date('now', 'start of year')"
        # period == 4 is All Time, no filter
        
        # Get breakdown by category
        # Get table name based on database type
        table_name = "costs" if hasattr(self.db_manager, 'supabase') else "expenses"
        date_col = "cost_date" if hasattr(self.db_manager, 'supabase') else "expense_date"
        
        # Adjust date filter for correct column
        if date_filter and hasattr(self.db_manager, 'supabase'):
            date_filter = date_filter.replace('expense_date', 'cost_date')
        
        breakdown = self.db_manager.execute_query(f"""
            SELECT category, SUM(amount) as total
            FROM {table_name}
            WHERE site_id = ? {date_filter}
            GROUP BY category
            ORDER BY total DESC
        """, (self.current_site_id,))
        
        self.breakdown_table.setRowCount(0)
        grand_total = 0
        
        if breakdown:
            for item in breakdown:
                if isinstance(item, dict):
                    cat_total = item.get('total', 0)
                    grand_total += cat_total
                else:
                    cat_total = item[1] if len(item) > 1 else 0
                    grand_total += cat_total
            
            # Add rows with percentages
            for item in breakdown:
                row = self.breakdown_table.rowCount()
                self.breakdown_table.insertRow(row)
                
                if isinstance(item, dict):
                    category = item['category']
                    amount = item['total']
                else:
                    category = item[0]
                    amount = item[1]
                
                percentage = (amount / grand_total * 100) if grand_total > 0 else 0
                
                self.breakdown_table.setItem(row, 0, QTableWidgetItem(category))
                self.breakdown_table.setItem(row, 1, QTableWidgetItem(f"IDR {amount:,.0f}"))
                self.breakdown_table.setItem(row, 2, QTableWidgetItem(f"{percentage:.1f}%"))
        
        # Get monthly summary
        # For Supabase, we need to get costs and aggregate in Python
        costs_query = f"SELECT expense_date, amount FROM costs WHERE site_id = ? {date_filter}"
        all_costs = self.db_manager.execute_query(costs_query, (self.current_site_id,))
        
        # Group by month in Python
        monthly_data = {}
        if all_costs:
            for cost in all_costs:
                if isinstance(cost, dict):
                    date_str = cost.get('expense_date')
                    amount = cost.get('amount', 0)
                else:
                    date_str = cost[0]
                    amount = cost[1] or 0
                
                if date_str:
                    # Extract year-month
                    try:
                        date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                        month_key = date_obj.strftime('%Y-%m')
                        
                        if month_key not in monthly_data:
                            monthly_data[month_key] = {'expenses': 0, 'labor': 0}
                        
                        monthly_data[month_key]['expenses'] += amount
                    except:
                        pass
        
        # Convert to list format expected by the display code
        monthly = []
        for month, data in sorted(monthly_data.items(), reverse=True)[:12]:
            monthly.append({
                'month': month,
                'expenses': data['expenses'],
                'labor': 0  # Labor calculation would need separate query
            })
        
        self.monthly_table.setRowCount(0)
        total_labor = 0
        
        if monthly:
            for item in monthly:
                row = self.monthly_table.rowCount()
                self.monthly_table.insertRow(row)
                
                if isinstance(item, dict):
                    month = datetime.strptime(item['month'], '%Y-%m').strftime('%B %Y')
                    expenses = item['expenses'] or 0
                    labor = item['labor'] or 0
                else:
                    month = datetime.strptime(item[0], '%Y-%m').strftime('%B %Y')
                    expenses = item[1] or 0
                    labor = item[2] or 0
                
                total_labor += labor
                
                self.monthly_table.setItem(row, 0, QTableWidgetItem(month))
                self.monthly_table.setItem(row, 1, QTableWidgetItem(f"IDR {expenses:,.0f}"))
                self.monthly_table.setItem(row, 2, QTableWidgetItem(f"IDR {labor:,.0f}"))
        
        # Update grand total
        self.grand_total_label.setText(
            self.tr(f"Total Project Cost: IDR {(grand_total + total_labor):,.0f}")
        )
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.expenses_table.selectedItems()) > 0
        self.edit_expense_action.setEnabled(has_selection)
        self.delete_expense_action.setEnabled(has_selection)
    
    def add_expense(self):
        """Add new expense"""
        if not self.current_site_id:
            QMessageBox.warning(
                self,
                self.tr("Warning"),
                self.tr("Please select a site first")
            )
            return
        
        dlg = ExpenseDialog(self.db_manager, self.current_site_id, parent=self)
        if dlg.exec_():
            data = dlg.get_expense_data()
            
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            
            if self.db_manager.execute_update(
                f"INSERT INTO expenses ({columns}) VALUES ({placeholders})",
                list(data.values())
            ):
                self.refresh_expenses()
                self.update_summary()
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Expense added successfully")
                )
    
    def edit_expense(self):
        """Edit selected expense"""
        if not self.expenses_table.selectedItems():
            return
        
        row = self.expenses_table.currentRow()
        expense_id = int(self.expenses_table.item(row, 0).text())
        
        dlg = ExpenseDialog(
            self.db_manager,
            self.current_site_id,
            expense_id=expense_id,
            parent=self
        )
        
        if dlg.exec_():
            data = dlg.get_expense_data()
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [expense_id]
            
            if self.db_manager.execute_update(
                f"UPDATE expenses SET {set_clause} WHERE id = ?",
                values
            ):
                self.refresh_expenses()
                self.update_summary()
    
    def delete_expense(self):
        """Delete selected expense"""
        if not self.expenses_table.selectedItems():
            return
        
        row = self.expenses_table.currentRow()
        expense_id = int(self.expenses_table.item(row, 0).text())
        description = self.expenses_table.item(row, 3).text()
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr(f"Delete expense: {description}?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.execute_update(
                "DELETE FROM expenses WHERE id = ?",
                (expense_id,)
            ):
                self.refresh_expenses()
                self.update_summary()
    
    def export_report(self):
        """Export cost report"""
        if not self.current_site_id:
            return
        
        # Get file path
        from qgis.PyQt.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Export Report"),
            f"excavation_costs_{date.today().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                import csv
                
                # Get all data
                expenses = self.db_manager.execute_query(
                    """SELECT expense_date, category, description, supplier,
                              amount, payment_method, receipt_number, approved_by, notes
                       FROM expenses
                       WHERE site_id = ?
                       ORDER BY expense_date DESC""",
                    (self.current_site_id,)
                )
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Header
                    writer.writerow([
                        'Date', 'Category', 'Description', 'Supplier',
                        'Amount (IDR)', 'Payment Method', 'Receipt #',
                        'Approved By', 'Notes'
                    ])
                    
                    # Data
                    for expense in expenses:
                        if isinstance(expense, dict):
                            row = [
                                expense['expense_date'],
                                expense['category'],
                                expense['description'],
                                expense['supplier'] or '',
                                expense['amount'],
                                expense['payment_method'],
                                expense['receipt_number'] or '',
                                expense['approved_by'] or '',
                                expense['notes'] or ''
                            ]
                        else:
                            row = list(expense)
                        
                        writer.writerow(row)
                
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Report exported successfully")
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr(f"Export failed: {str(e)}")
                )
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('CostsWidget', message)