# -*- coding: utf-8 -*-
"""Site management widget"""

from qgis.PyQt.QtCore import Qt, QDateTime, pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QToolBar,
                                QLineEdit, QLabel, QMessageBox, QHeaderView,
                                QFormLayout, QDialog, QDialogButtonBox,
                                QTextEdit, QDateEdit, QSpinBox, QDoubleSpinBox,
                                QComboBox)
from qgis.PyQt.QtGui import QIcon
from qgis.core import (QgsFeature, QgsGeometry, QgsRectangle, QgsProject,
                      QgsVectorLayer)
from qgis.gui import QgsMapToolExtent
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
plugin_dir = os.path.dirname(os.path.dirname(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from ui.media_list_widget import MediaListWidget

class SiteDialog(QDialog):
    """Dialog for adding/editing sites"""
    
    def __init__(self, db_manager, site_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.site_id = site_id
        self.setWindowTitle(self.tr("Site Details"))
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.init_ui()
        
        if site_id:
            self.load_site_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        
        # Site code
        self.site_code_edit = QLineEdit()
        self.site_code_edit.setPlaceholderText("e.g., BTN2025-01")
        form_layout.addRow(self.tr("Site Code:"), self.site_code_edit)
        
        # Site name
        self.site_name_edit = QLineEdit()
        form_layout.addRow(self.tr("Site Name:"), self.site_name_edit)
        
        # Discovery date
        self.discovery_date = QDateEdit()
        self.discovery_date.setCalendarPopup(True)
        self.discovery_date.setDate(QDateTime.currentDateTime().date())
        form_layout.addRow(self.tr("Discovery Date:"), self.discovery_date)
        
        # Period
        period_layout = QHBoxLayout()
        self.period_from_edit = QLineEdit()
        self.period_from_edit.setPlaceholderText("e.g., 14th century")
        period_layout.addWidget(self.period_from_edit)
        period_layout.addWidget(QLabel(self.tr("to")))
        self.period_to_edit = QLineEdit()
        self.period_to_edit.setPlaceholderText("e.g., 15th century")
        period_layout.addWidget(self.period_to_edit)
        form_layout.addRow(self.tr("Period:"), period_layout)
        
        # Vessel type
        self.vessel_type_combo = QComboBox()
        self.vessel_type_combo.setEditable(True)
        self.vessel_type_combo.addItems([
            "", "Junk", "Dhow", "Galleon", "Merchant vessel", 
            "Warship", "Unknown"
        ])
        form_layout.addRow(self.tr("Vessel Type:"), self.vessel_type_combo)
        
        # Dimensions
        dim_layout = QHBoxLayout()
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setMaximum(999.99)
        self.length_spin.setSuffix(" m")
        dim_layout.addWidget(QLabel(self.tr("Length:")))
        dim_layout.addWidget(self.length_spin)
        
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setMaximum(999.99)
        self.width_spin.setSuffix(" m")
        dim_layout.addWidget(QLabel(self.tr("Width:")))
        dim_layout.addWidget(self.width_spin)
        form_layout.addRow(self.tr("Estimated Size:"), dim_layout)
        
        # Depth range
        depth_layout = QHBoxLayout()
        self.depth_min_spin = QDoubleSpinBox()
        self.depth_min_spin.setMaximum(999.99)
        self.depth_min_spin.setSuffix(" m")
        depth_layout.addWidget(QLabel(self.tr("Min:")))
        depth_layout.addWidget(self.depth_min_spin)
        
        self.depth_max_spin = QDoubleSpinBox()
        self.depth_max_spin.setMaximum(999.99)
        self.depth_max_spin.setSuffix(" m")
        depth_layout.addWidget(QLabel(self.tr("Max:")))
        depth_layout.addWidget(self.depth_max_spin)
        form_layout.addRow(self.tr("Depth Range:"), depth_layout)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow(self.tr("Description:"), self.description_edit)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["active", "completed", "suspended"])
        form_layout.addRow(self.tr("Status:"), self.status_combo)
        
        layout.addLayout(form_layout)
        
        # Media widget
        self.media_widget = MediaListWidget(self.db_manager, 'site', self.site_id, self)
        layout.addWidget(self.media_widget)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def load_site_data(self):
        """Load existing site data"""
        site = self.db_manager.execute_query(
            "SELECT * FROM sites WHERE id = ?", (self.site_id,)
        )
        
        if site:
            data = site[0]
            # Handle both dict and tuple
            if isinstance(data, dict):
                self.site_code_edit.setText(data.get('site_code', ''))
                self.site_name_edit.setText(data.get('site_name', ''))
                # Add other fields...
            else:
                # Tuple access by index
                self.site_code_edit.setText(data[1] if len(data) > 1 else '')
                self.site_name_edit.setText(data[2] if len(data) > 2 else '')
    
    def get_site_data(self):
        """Get site data from form"""
        return {
            'site_code': self.site_code_edit.text(),
            'site_name': self.site_name_edit.text(),
            'discovery_date': self.discovery_date.date().toString('yyyy-MM-dd'),
            'period_from': self.period_from_edit.text(),
            'period_to': self.period_to_edit.text(),
            'vessel_type': self.vessel_type_combo.currentText(),
            'estimated_length': self.length_spin.value() if self.length_spin.value() > 0 else None,
            'estimated_width': self.width_spin.value() if self.width_spin.value() > 0 else None,
            'depth_min': self.depth_min_spin.value() if self.depth_min_spin.value() > 0 else None,
            'depth_max': self.depth_max_spin.value() if self.depth_max_spin.value() > 0 else None,
            'description': self.description_edit.toPlainText(),
            'status': self.status_combo.currentText()
        }
    
    def accept(self):
        """Validate and save"""
        if not self.site_code_edit.text() or not self.site_name_edit.text():
            QMessageBox.warning(
                self, 
                self.tr("Warning"),
                self.tr("Site code and name are required")
            )
            return
        
        super().accept()
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('SiteDialog', message)

class SiteWidget(QWidget):
    """Widget for managing archaeological sites"""
    
    site_selected = pyqtSignal(int)
    sites_updated = pyqtSignal()  # Emitted when sites are added/updated/deleted
    
    def __init__(self, iface, db_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.db_manager = db_manager
        
        # Connect to database error signal
        self.db_manager.db_error.connect(self.show_db_error)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Actions
        self.add_action = toolbar.addAction(self.tr("Add Site"))
        self.add_action.triggered.connect(self.add_site)
        
        self.edit_action = toolbar.addAction(self.tr("Edit Site"))
        self.edit_action.triggered.connect(self.edit_site)
        self.edit_action.setEnabled(False)
        
        self.delete_action = toolbar.addAction(self.tr("Delete Site"))
        self.delete_action.triggered.connect(self.delete_site)
        self.delete_action.setEnabled(False)
        
        toolbar.addSeparator()
        
        self.draw_action = toolbar.addAction(self.tr("Draw Site Boundary"))
        self.draw_action.setCheckable(True)
        self.draw_action.triggered.connect(self.toggle_draw_tool)
        
        toolbar.addSeparator()
        
        # Search
        toolbar.addWidget(QLabel(self.tr("Search:")))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Site name or code..."))
        self.search_edit.textChanged.connect(self.filter_sites)
        toolbar.addWidget(self.search_edit)
        
        layout.addWidget(toolbar)
        
        # Sites table
        self.sites_table = QTableWidget()
        self.sites_table.setColumnCount(9)  # Added Media column
        self.sites_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Site Code"), self.tr("Site Name"),
            self.tr("Vessel Type"), self.tr("Period"), self.tr("Depth Range"),
            self.tr("Media"), self.tr("Status"), self.tr("Discovery Date")
        ])
        
        # Hide ID column
        self.sites_table.hideColumn(0)
        
        # Set column widths
        header = self.sites_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Site name
        
        # Selection
        self.sites_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sites_table.setSelectionMode(QTableWidget.SingleSelection)
        self.sites_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.sites_table.cellDoubleClicked.connect(self.edit_site)
        
        layout.addWidget(self.sites_table)
        
        # Status
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Map tool
        self.map_tool = None
        
    def refresh_data(self):
        """Refresh sites table"""
        sites = self.db_manager.execute_query(
            """SELECT s.id, s.site_code, s.site_name, s.vessel_type, 
                      s.period_from || ' - ' || s.period_to as period,
                      s.depth_min || ' - ' || s.depth_max || ' m' as depth_range,
                      COUNT(DISTINCT mr.media_id) as media_count,
                      s.status, s.discovery_date
               FROM sites s
               LEFT JOIN media_relations mr ON mr.related_id = s.id AND mr.related_type = 'site'
               GROUP BY s.id, s.site_code, s.site_name, s.vessel_type, s.period_from, 
                        s.period_to, s.depth_min, s.depth_max, s.status, s.discovery_date
               ORDER BY s.site_code"""
        )
        
        self.sites_table.setRowCount(0)
        
        if sites:
            self.sites_table.setRowCount(len(sites))
            
            for row, site in enumerate(sites):
                # Handle both dict and tuple
                if isinstance(site, dict):
                    values = [
                        str(site.get('id', '')),
                        site.get('site_code', ''),
                        site.get('site_name', ''),
                        site.get('vessel_type', ''),
                        site.get('period', ''),
                        site.get('depth_range', ''),
                        str(site.get('media_count', 0)),
                        site.get('status', ''),
                        site.get('discovery_date', '')
                    ]
                else:
                    # For tuple, media_count is at index 6
                    values = []
                    for i, v in enumerate(site):
                        if i == 6:  # media_count column
                            values.append(str(v) if v else '0')
                        else:
                            values.append(str(v) if v else '')
                
                for col, value in enumerate(values):
                    self.sites_table.setItem(row, col, QTableWidgetItem(value))
        
        self.update_status()
    
    def filter_sites(self):
        """Filter sites based on search"""
        search_text = self.search_edit.text().lower()
        
        for row in range(self.sites_table.rowCount()):
            show_row = True
            
            if search_text:
                site_code = self.sites_table.item(row, 1).text().lower()
                site_name = self.sites_table.item(row, 2).text().lower()
                if search_text not in site_code and search_text not in site_name:
                    show_row = False
            
            self.sites_table.setRowHidden(row, not show_row)
        
        self.update_status()
    
    def update_status(self):
        """Update status label"""
        total = self.sites_table.rowCount()
        visible = sum(1 for row in range(total) if not self.sites_table.isRowHidden(row))
        
        if total == visible:
            self.status_label.setText(self.tr(f"Total sites: {total}"))
        else:
            self.status_label.setText(self.tr(f"Showing {visible} of {total} sites"))
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.sites_table.selectedItems()) > 0
        self.edit_action.setEnabled(has_selection)
        self.delete_action.setEnabled(has_selection)
        
        if has_selection:
            row = self.sites_table.currentRow()
            site_id = int(self.sites_table.item(row, 0).text())
            self.site_selected.emit(site_id)
    
    def add_site(self):
        """Add new site"""
        dlg = SiteDialog(self.db_manager, parent=self)
        if dlg.exec_():
            data = dlg.get_site_data()
            print(f"DEBUG: Site data to save: {data}")
            
            # Insert site
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            query = f"INSERT INTO sites ({columns}) VALUES ({placeholders})"
            values = list(data.values())
            
            print(f"DEBUG: Query: {query}")
            print(f"DEBUG: Values: {values}")
            
            result = self.db_manager.execute_update(query, values)
            print(f"DEBUG: Insert result: {result}")
            
            if result:
                self.refresh_data()
                self.sites_updated.emit()  # Notify other widgets
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Site added successfully")
                )
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr("Failed to add site. Check the console for details.")
                )
    
    def edit_site(self):
        """Edit selected site"""
        if not self.sites_table.selectedItems():
            return
        
        row = self.sites_table.currentRow()
        site_id = int(self.sites_table.item(row, 0).text())
        
        dlg = SiteDialog(self.db_manager, site_id=site_id, parent=self)
        if dlg.exec_():
            data = dlg.get_site_data()
            
            # Update site
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [site_id]
            
            if self.db_manager.execute_update(
                f"UPDATE sites SET {set_clause} WHERE id = ?",
                values
            ):
                self.refresh_data()
                self.sites_updated.emit()  # Notify other widgets
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Site updated successfully")
                )
    
    def delete_site(self):
        """Delete selected site"""
        if not self.sites_table.selectedItems():
            return
        
        row = self.sites_table.currentRow()
        site_id = int(self.sites_table.item(row, 0).text())
        site_name = self.sites_table.item(row, 2).text()
        
        # Check if site has finds
        finds_count = self.db_manager.execute_query(
            "SELECT COUNT(*) as count FROM finds WHERE site_id = ?",
            (site_id,)
        )[0]
        
        count = finds_count[0] if isinstance(finds_count, tuple) else finds_count.get('count', 0)
        
        if count > 0:
            QMessageBox.warning(
                self,
                self.tr("Cannot Delete"),
                self.tr(f"Cannot delete site '{site_name}' because it has {count} associated finds")
            )
            return
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr(f"Are you sure you want to delete site '{site_name}'?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.execute_update("DELETE FROM sites WHERE id = ?", (site_id,)):
                self.refresh_data()
                self.sites_updated.emit()  # Notify other widgets
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Site deleted successfully")
                )
    
    def toggle_draw_tool(self, checked):
        """Toggle site boundary drawing tool"""
        if checked:
            # Create map tool for drawing rectangles
            self.map_tool = QgsMapToolExtent(self.iface.mapCanvas())
            self.map_tool.extentChanged.connect(self.on_extent_drawn)
            self.iface.mapCanvas().setMapTool(self.map_tool)
        else:
            if self.map_tool:
                self.iface.mapCanvas().unsetMapTool(self.map_tool)
                self.map_tool = None
    
    def on_extent_drawn(self, extent):
        """Handle drawn extent"""
        # Create polygon from extent
        geom = QgsGeometry.fromRect(extent)
        
        # Add site with geometry
        dlg = SiteDialog(self.db_manager, parent=self)
        if dlg.exec_():
            data = dlg.get_site_data()
            
            # Add geometry
            columns = ', '.join(data.keys()) + ', geom'
            if self.db_manager.spatialite_available:
                placeholders = ', '.join(['?' for _ in data]) + ', GeomFromText(?, 32648)'
            else:
                placeholders = ', '.join(['?' for _ in data]) + ', ?'
            values = list(data.values()) + [geom.asWkt()]
            
            if self.db_manager.execute_update(
                f"INSERT INTO sites ({columns}) VALUES ({placeholders})",
                values
            ):
                self.refresh_data()
                self.db_manager.add_layers_to_qgis(['sites'])
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Site added with boundary")
                )
        
        # Uncheck draw action
        self.draw_action.setChecked(False)
        self.toggle_draw_tool(False)
    
    def show_db_error(self, error_msg):
        """Show database error to user"""
        QMessageBox.critical(
            self,
            self.tr("Database Error"),
            error_msg
        )
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('SiteWidget', message)