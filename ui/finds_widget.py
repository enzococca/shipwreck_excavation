# -*- coding: utf-8 -*-
"""
Finds management widget
"""

from qgis.PyQt.QtCore import Qt, QDateTime, pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QTableWidget, QTableWidgetItem, QToolBar,
                                QLineEdit, QComboBox, QLabel, QMessageBox,
                                QHeaderView, QMenu, QAction, QFileDialog)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings
from qgis.core import (QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                      QgsVectorLayer)
from qgis.gui import QgsMapToolEmitPoint, QgsMapTool, QgsRubberBand

import os
from datetime import datetime

class FindsWidget(QWidget):
    """Widget for managing archaeological finds"""
    
    find_selected = pyqtSignal(int)  # Emitted when a find is selected
    
    def __init__(self, iface, db_manager, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.db_manager = db_manager
        self.current_site_id = None
        
        self.init_ui()
        self.load_sites()
        
    def init_ui(self):
        """Initialize the user interface"""
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
        self.add_action = QAction(QIcon(), self.tr("Add Find"), self)
        self.add_action.triggered.connect(self.add_find)
        toolbar.addAction(self.add_action)
        
        self.edit_action = QAction(QIcon(), self.tr("Edit Find"), self)
        self.edit_action.triggered.connect(self.edit_find)
        self.edit_action.setEnabled(False)
        toolbar.addAction(self.edit_action)
        
        self.delete_action = QAction(QIcon(), self.tr("Delete Find"), self)
        self.delete_action.triggered.connect(self.delete_find)
        self.delete_action.setEnabled(False)
        toolbar.addAction(self.delete_action)
        
        toolbar.addSeparator()
        
        self.map_tool_action = QAction(QIcon(), self.tr("Pick Location"), self)
        self.map_tool_action.setCheckable(True)
        self.map_tool_action.triggered.connect(self.toggle_map_tool)
        toolbar.addAction(self.map_tool_action)
        
        toolbar.addSeparator()
        
        # Export action
        self.export_action = QAction(QIcon(), self.tr("Export Finds"), self)
        self.export_action.triggered.connect(self.export_finds)
        toolbar.addAction(self.export_action)
        
        toolbar.addSeparator()
        
        # Search
        toolbar.addWidget(QLabel(self.tr("Search:")))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Find number or description..."))
        self.search_edit.textChanged.connect(self.filter_finds)
        toolbar.addWidget(self.search_edit)
        
        # Material type filter - updated with all material types
        toolbar.addWidget(QLabel(self.tr("Material:")))
        self.material_combo = QComboBox()
        self.material_combo.addItem(self.tr("All"))
        # Add all material types from database
        material_types = [
            "Black/Red Ware", "Stoneware", "Ceramic", "Porcelain", "Celadon", 
            "Martaban", "Mercury Jar", "Metal", "Wood", "Glass", "Stone Tool", 
            "Bone", "Shell/Pearl", "Organic (Nut/Seed)", "Organic Material", 
            "Fiber/Rope", "Resin", "Sediment", "Clay", "Horn", "Weight", "Other"
        ]
        self.material_combo.addItems(material_types)
        self.material_combo.currentTextChanged.connect(self.filter_finds)
        toolbar.addWidget(self.material_combo)
        
        layout.addWidget(toolbar)
        
        # Finds table - updated with new columns
        self.finds_table = QTableWidget()
        self.finds_table.setColumnCount(15)  # Increased column count
        self.finds_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Find Number"), self.tr("Inv No"), 
            self.tr("Year"), self.tr("Material"), self.tr("Object Type"), 
            self.tr("Section"), self.tr("SU"), self.tr("Storage"),
            self.tr("Quantity"), self.tr("Dimensions"), self.tr("Description"), 
            self.tr("Condition"), self.tr("Depth (m)"), self.tr("Media")
        ])
        
        # Hide ID column
        self.finds_table.hideColumn(0)
        
        # Set column widths
        header = self.finds_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(11, QHeaderView.Stretch)  # Description column (now at index 11)
        
        # Enable sorting
        self.finds_table.setSortingEnabled(True)
        
        # Selection behavior
        self.finds_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.finds_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Connect signals
        self.finds_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.finds_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        # Context menu
        self.finds_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.finds_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.finds_table)
        
        # Status bar
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Map tool
        self.map_tool = None
        self.rubber_band = None
        
    def load_sites(self):
        """Load sites into combo box"""
        self.site_combo.clear()
        self.site_combo.addItem(self.tr("Select Site..."), None)
        
        sites = self.db_manager.execute_query("SELECT id, site_name FROM sites ORDER BY site_name")
        if sites:
            for site in sites:
                # Handle both dict and tuple results
                if isinstance(site, dict):
                    self.site_combo.addItem(site['site_name'], site['id'])
                else:
                    self.site_combo.addItem(site[1], site[0])  # site_name, id
    
    def on_site_changed(self, index):
        """Handle site selection change"""
        self.current_site_id = self.site_combo.currentData()
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh finds table"""
        if not self.current_site_id:
            self.finds_table.setRowCount(0)
            self.update_status()
            return
        
        # Get finds for current site
        finds = self.db_manager.get_finds(site_id=self.current_site_id)
        
        # Clear table
        self.finds_table.setRowCount(0)
        
        if finds:
            self.finds_table.setRowCount(len(finds))
            
            for row, find in enumerate(finds):
                # Handle both dict and tuple access
                def get_value(find, key, default=''):
                    if isinstance(find, dict):
                        return find.get(key, default)
                    return default
                
                col = 0
                # ID (hidden)
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'id'))))
                col += 1
                
                # Find Number
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'find_number'))))
                col += 1
                
                # Inv No (new)
                inv_no = get_value(find, 'inv_no', '')
                self.finds_table.setItem(row, col, QTableWidgetItem(str(inv_no) if inv_no else ''))
                col += 1
                
                # Year (new)
                year = get_value(find, 'year', '')
                self.finds_table.setItem(row, col, QTableWidgetItem(str(year) if year else ''))
                col += 1
                
                # Material
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'material_type'))))
                col += 1
                
                # Object Type
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'object_type'))))
                col += 1
                
                # Section (new)
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'section'))))
                col += 1
                
                # SU (new)
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'su'))))
                col += 1
                
                # Storage Location (new)
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'storage_location'))))
                col += 1
                
                # Quantity (new)
                quantity = get_value(find, 'quantity', '')
                self.finds_table.setItem(row, col, QTableWidgetItem(str(quantity) if quantity else ''))
                col += 1
                
                # Dimensions (new)
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'dimensions'))))
                col += 1
                
                # Description
                desc = get_value(find, 'description', '')
                # Truncate long descriptions for table display
                if len(desc) > 100:
                    desc = desc[:100] + '...'
                self.finds_table.setItem(row, col, QTableWidgetItem(desc))
                col += 1
                
                # Condition
                self.finds_table.setItem(row, col, QTableWidgetItem(str(get_value(find, 'condition'))))
                col += 1
                
                # Depth
                depth = get_value(find, 'depth')
                if depth:
                    try:
                        self.finds_table.setItem(row, col, QTableWidgetItem(f"{float(depth):.2f}"))
                    except:
                        self.finds_table.setItem(row, col, QTableWidgetItem(str(depth)))
                else:
                    self.finds_table.setItem(row, col, QTableWidgetItem(''))
                col += 1
                
                # Media count
                media_count = get_value(find, 'media_count', 0)
                if media_count and int(media_count) > 0:
                    item = QTableWidgetItem(f"📎 {media_count}")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.finds_table.setItem(row, col, item)
                else:
                    self.finds_table.setItem(row, col, QTableWidgetItem(''))
        
        # Re-apply filter after refreshing data
        self.filter_finds()
        self.update_status()
    
    def filter_finds(self):
        """Filter finds based on search criteria"""
        search_text = self.search_edit.text().lower()
        material_filter = self.material_combo.currentText()
        
        for row in range(self.finds_table.rowCount()):
            show_row = True
            
            # Text search - search across ALL fields
            if search_text:
                row_text = ""
                # Concatenate all column texts (skip ID column at index 0)
                for col in range(1, self.finds_table.columnCount()):
                    item = self.finds_table.item(row, col)
                    if item:
                        row_text += item.text().lower() + " "
                
                # Check if search text is in any field
                if search_text not in row_text:
                    show_row = False
            
            # Material filter
            if material_filter != self.tr("All"):
                material_item = self.finds_table.item(row, 4)  # Material column (new index)
                material = material_item.text() if material_item else ""
                if material != material_filter:
                    show_row = False
            
            self.finds_table.setRowHidden(row, not show_row)
        
        self.update_status()
    
    def update_status(self):
        """Update status label"""
        total = self.finds_table.rowCount()
        visible = sum(1 for row in range(total) if not self.finds_table.isRowHidden(row))
        
        if total == visible:
            self.status_label.setText(self.tr(f"Total finds: {total}"))
        else:
            self.status_label.setText(self.tr(f"Showing {visible} of {total} finds"))
    
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = len(self.finds_table.selectedItems()) > 0
        self.edit_action.setEnabled(has_selection)
        self.delete_action.setEnabled(has_selection)
        
        if has_selection:
            row = self.finds_table.currentRow()
            find_id = int(self.finds_table.item(row, 0).text())
            self.find_selected.emit(find_id)
    
    def on_cell_double_clicked(self, row, column):
        """Handle double click on cell"""
        if column == 9:  # Coordinates column
            # Zoom to find location
            find_id = int(self.finds_table.item(row, 0).text())
            self.zoom_to_find(find_id)
        else:
            self.edit_find()
    
    def show_context_menu(self, position):
        """Show context menu"""
        if not self.finds_table.selectedItems():
            return
        
        menu = QMenu()
        
        edit_action = menu.addAction(self.tr("Edit"))
        edit_action.triggered.connect(self.edit_find)
        
        delete_action = menu.addAction(self.tr("Delete"))
        delete_action.triggered.connect(self.delete_find)
        
        menu.addSeparator()
        
        zoom_action = menu.addAction(self.tr("Zoom to Location"))
        zoom_action.triggered.connect(lambda: self.zoom_to_find(self.get_selected_find_id()))
        
        add_media_action = menu.addAction(self.tr("Add Media"))
        add_media_action.triggered.connect(self.add_media_to_find)
        
        menu.exec_(self.finds_table.mapToGlobal(position))
    
    def add_find(self):
        """Add new find"""
        if not self.current_site_id:
            QMessageBox.warning(self, self.tr("Warning"), self.tr("Please select a site first"))
            return
        
        from .find_dialog import FindDialog
        
        dlg = FindDialog(self.db_manager, self.current_site_id, parent=self)
        if dlg.exec_():
            # Get data from dialog
            data = dlg.get_find_data()
            
            # Save to database
            find_id = self.db_manager.add_find(data)
            
            if find_id:
                self.refresh_data()
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Find added successfully")
                )
            else:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr("Failed to add find")
                )
    
    def edit_find(self):
        """Edit selected find"""
        find_id = self.get_selected_find_id()
        if not find_id:
            return
        
        from .find_dialog import FindDialog
        
        dlg = FindDialog(self.db_manager, self.current_site_id, find_id=find_id, parent=self)
        if dlg.exec_():
            # Get data from dialog
            data = dlg.get_find_data()
            
            # Update in database
            set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
            values = list(data.values()) + [find_id]
            
            if self.db_manager.execute_update(
                f"UPDATE finds SET {set_clause} WHERE id = ?",
                values
            ):
                self.refresh_data()
                QMessageBox.information(
                    self,
                    self.tr("Success"),
                    self.tr("Find updated successfully")
                )
    
    def delete_find(self):
        """Delete selected find"""
        find_id = self.get_selected_find_id()
        if not find_id:
            return
        
        reply = QMessageBox.question(
            self,
            self.tr("Confirm Delete"),
            self.tr("Are you sure you want to delete this find?"),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.execute_update("DELETE FROM finds WHERE id = ?", (find_id,)):
                self.refresh_data()
                QMessageBox.information(self, self.tr("Success"), self.tr("Find deleted successfully"))
    
    def get_selected_find_id(self):
        """Get ID of selected find"""
        if not self.finds_table.selectedItems():
            return None
        
        row = self.finds_table.currentRow()
        find_id = int(self.finds_table.item(row, 0).text())
        find_number = self.finds_table.item(row, 1).text() if self.finds_table.item(row, 1) else "Unknown"
        print(f"DEBUG: Selected find - Row: {row}, ID: {find_id}, Number: {find_number}")
        return find_id
    
    def toggle_map_tool(self, checked):
        """Toggle map tool for picking location"""
        if checked:
            self.map_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
            self.map_tool.canvasClicked.connect(self.on_map_clicked)
            self.iface.mapCanvas().setMapTool(self.map_tool)
            
            # Create rubber band for visual feedback
            from qgis.core import QgsWkbTypes
            self.rubber_band = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
            self.rubber_band.setColor(Qt.red)
            self.rubber_band.setWidth(2)
        else:
            if self.map_tool:
                self.iface.mapCanvas().unsetMapTool(self.map_tool)
                self.map_tool = None
            
            if self.rubber_band:
                self.rubber_band.reset()
                self.rubber_band = None
    
    def on_map_clicked(self, point, button):
        """Handle map click"""
        if button == Qt.LeftButton:
            # Add point to rubber band
            if self.rubber_band:
                self.rubber_band.reset()
                self.rubber_band.addPoint(point)
            
            # Store the point for use in find dialog
            self.last_picked_point = point
            
            # Show message
            self.iface.messageBar().pushMessage(
                self.tr("Location Selected"),
                f"Coordinates: {point.x():.2f}, {point.y():.2f}",
                level=0,  # Info
                duration=3
            )
    
    def zoom_to_find(self, find_id):
        """Zoom to find location on map"""
        result = self.db_manager.execute_query(
            "SELECT AsText(geom) as geom_wkt FROM finds WHERE id = ?",
            (find_id,)
        )
        
        if result and result[0]['geom_wkt']:
            geom = QgsGeometry.fromWkt(result[0]['geom_wkt'])
            if not geom.isEmpty():
                self.iface.mapCanvas().setExtent(geom.boundingBox())
                self.iface.mapCanvas().refresh()
    
    def add_media_to_find(self):
        """Add media to selected find"""
        find_id = self.get_selected_find_id()
        if not find_id:
            return
        
        # This would open a media dialog
        # For now, just show a message
        QMessageBox.information(
            self,
            self.tr("Add Media"),
            self.tr("Media management will be implemented in the Media tab")
        )
    
    def tr(self, message):
        """Get translation"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('FindsWidget', message)
    
    def export_finds(self):
        """Export finds list or details"""
        if not self.current_site_id:
            QMessageBox.warning(
                self,
                self.tr("No Site Selected"),
                self.tr("Please select a site first")
            )
            return
        
        # Ask user what to export
        from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QDialogButtonBox, QCheckBox, QComboBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Export Finds"))
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout()
        
        # Export type
        layout.addWidget(QLabel(self.tr("Export type:")))
        list_radio = QRadioButton(self.tr("Finds list (all finds)"))
        list_radio.setChecked(True)
        detail_radio = QRadioButton(self.tr("Find details (selected find)"))
        
        layout.addWidget(list_radio)
        layout.addWidget(detail_radio)
        
        # Include photos option
        photos_check = QCheckBox(self.tr("Include photos"))
        photos_check.setChecked(True)
        layout.addWidget(photos_check)
        
        # Language selection
        layout.addWidget(QLabel(self.tr("Language:")))
        lang_combo = QComboBox()
        lang_combo.addItem("English", "en")
        lang_combo.addItem("Indonesian", "id")
        
        # Get current language from settings
        settings = QSettings()
        current_lang = settings.value('shipwreck_excavation/language', 'en')
        index = lang_combo.findData(current_lang)
        if index >= 0:
            lang_combo.setCurrentIndex(index)
        
        layout.addWidget(lang_combo)
        
        # Format selection
        layout.addWidget(QLabel(self.tr("Format:")))
        html_radio = QRadioButton("HTML")
        html_radio.setChecked(True)
        pdf_radio = QRadioButton("PDF")
        layout.addWidget(html_radio)
        layout.addWidget(pdf_radio)
        
        # Enable/disable detail option based on selection
        def check_selection():
            try:
                has_selection = self.finds_table.currentRow() >= 0
                detail_radio.setEnabled(has_selection)
                if not has_selection and detail_radio.isChecked():
                    list_radio.setChecked(True)
            except RuntimeError:
                # Dialog has been closed, disconnect signal
                try:
                    self.finds_table.itemSelectionChanged.disconnect(check_selection)
                except:
                    pass
        
        # Initial check
        check_selection()
        
        # Store connection for later cleanup
        selection_connection = None
        try:
            # Connect only if dialog is visible
            selection_connection = self.finds_table.itemSelectionChanged.connect(check_selection)
        except:
            pass
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        result = dialog.exec_()
        
        # Disconnect signal to avoid errors
        try:
            self.finds_table.itemSelectionChanged.disconnect(check_selection)
        except:
            pass
        
        if result:
            # Import exporter
            try:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from utils.finds_exporter import FindsExporter
                
                exporter = FindsExporter(self.db_manager)
                exporter.set_language(lang_combo.currentData())
                
                # Determine what to export
                if list_radio.isChecked():
                    # Export list
                    site = self.db_manager.execute_query(
                        "SELECT site_name FROM sites WHERE id = ?",
                        (self.current_site_id,)
                    )[0]
                    site_name = site['site_name'] if isinstance(site, dict) else site[0]
                    
                    if html_radio.isChecked():
                        filename, _ = QFileDialog.getSaveFileName(
                            self,
                            self.tr("Save Finds List"),
                            f"finds_list_{site_name}.html",
                            "HTML Files (*.html)"
                        )
                        if filename:
                            success = exporter.export_finds_list_html(
                                self.current_site_id, filename, 
                                include_photos=photos_check.isChecked()
                            )
                    else:
                        filename, _ = QFileDialog.getSaveFileName(
                            self,
                            self.tr("Save Finds List"),
                            f"finds_list_{site_name}.pdf",
                            "PDF Files (*.pdf)"
                        )
                        if filename:
                            success = exporter.export_finds_list_pdf(
                                self.current_site_id, filename,
                                include_photos=photos_check.isChecked()
                            )
                else:
                    # Export selected find details
                    row = self.finds_table.currentRow()
                    if row >= 0:
                        find_id = int(self.finds_table.item(row, 0).text())
                        find_number = self.finds_table.item(row, 1).text()
                        
                        filename, _ = QFileDialog.getSaveFileName(
                            self,
                            self.tr("Save Find Details"),
                            f"find_details_{find_number}.pdf",
                            "PDF Files (*.pdf)"
                        )
                        if filename:
                            success = exporter.export_find_details_pdf(find_id, filename)
                
                if 'success' in locals() and success:
                    QMessageBox.information(
                        self,
                        self.tr("Success"),
                        self.tr("Export completed successfully")
                    )
                    
                    # Ask if user wants to open the file
                    reply = QMessageBox.question(
                        self,
                        self.tr("Open File"),
                        self.tr("Do you want to open the exported file?"),
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes and 'filename' in locals():
                        import subprocess
                        import platform
                        if platform.system() == 'Darwin':
                            subprocess.call(['open', filename])
                        elif platform.system() == 'Windows':
                            os.startfile(filename)
                        else:
                            subprocess.call(['xdg-open', filename])
                            
            except ImportError as e:
                if "reportlab" in str(e).lower():
                    QMessageBox.warning(
                        self,
                        self.tr("Missing Module"),
                        self.tr("ReportLab is required for PDF export. Please install it with: pip install reportlab")
                    )
                else:
                    raise
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tr("Error"),
                    self.tr(f"Export failed: {str(e)}")
                )