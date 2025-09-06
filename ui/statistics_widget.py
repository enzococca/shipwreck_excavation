# -*- coding: utf-8 -*-
"""Statistics widget for archaeological finds"""

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QGroupBox, QGridLayout, QComboBox,
                                QScrollArea, QFrame, QSplitter)
from qgis.PyQt.QtGui import QPainter, QColor, QFont, QPen, QBrush
from qgis.core import QgsMessageLog, Qgis
import os
import sys

# Check if matplotlib is available
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    QgsMessageLog.logMessage("Matplotlib not available - charts will be disabled", "Statistics", Qgis.Warning)

class StatisticsWidget(QWidget):
    """Widget for displaying finds statistics and charts"""
    
    def __init__(self, db_manager, site_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.site_id = site_id
        self.filters = {}  # Store active filters
        self.init_ui()
        self.refresh_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with site selector
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel(self.tr("Site:")))
        
        self.site_combo = QComboBox()
        self.site_combo.addItem(self.tr("All Sites"), None)
        self.load_sites()
        self.site_combo.currentIndexChanged.connect(self.on_site_changed)
        header_layout.addWidget(self.site_combo)
        
        # Add year filter
        header_layout.addWidget(QLabel(self.tr("Year:")))
        self.year_combo = QComboBox()
        self.year_combo.addItem(self.tr("All Years"), None)
        self.load_years()
        self.year_combo.currentIndexChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.year_combo)
        
        # Add material filter for debugging
        header_layout.addWidget(QLabel(self.tr("Material:")))
        self.material_combo = QComboBox()
        self.material_combo.addItem(self.tr("All Materials"), None)
        self.load_materials()
        self.material_combo.currentIndexChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.material_combo)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton(self.tr("Refresh"))
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Create splitter for stats and charts
        splitter = QSplitter(Qt.Vertical)
        
        # Statistics panel
        stats_group = QGroupBox(self.tr("Statistics Summary"))
        self.stats_layout = QGridLayout()
        stats_group.setLayout(self.stats_layout)
        splitter.addWidget(stats_group)
        
        # Charts panel
        if MATPLOTLIB_AVAILABLE:
            charts_group = QGroupBox(self.tr("Charts"))
            charts_layout = QVBoxLayout()
            
            # Chart type selector
            chart_selector = QHBoxLayout()
            chart_selector.addWidget(QLabel(self.tr("Chart Type:")))
            
            self.chart_combo = QComboBox()
            self.chart_combo.addItems([
                self.tr("Finds by Material"),
                self.tr("Finds by Object Type"),
                self.tr("Finds by Period"),
                self.tr("Finds Timeline"),
                self.tr("Depth Distribution"),
                self.tr("Conservation Status"),
                self.tr("Top Categories"),
                self.tr("Material vs Depth"),
                self.tr("Material vs Period")
            ])
            self.chart_combo.currentIndexChanged.connect(self.update_chart)
            chart_selector.addWidget(self.chart_combo)
            chart_selector.addStretch()
            
            charts_layout.addLayout(chart_selector)
            
            # Chart canvas
            self.figure = Figure(figsize=(10, 6))
            self.canvas = FigureCanvas(self.figure)
            charts_layout.addWidget(self.canvas)
            
            charts_group.setLayout(charts_layout)
            splitter.addWidget(charts_group)
        else:
            # Fallback if matplotlib not available
            no_charts = QLabel(self.tr("Charts not available - install matplotlib"))
            no_charts.setAlignment(Qt.AlignCenter)
            splitter.addWidget(no_charts)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def load_sites(self):
        """Load sites into combo box"""
        sites = self.db_manager.get_sites()
        for site in sites:
            self.site_combo.addItem(
                f"{site.get('site_code', '')} - {site.get('site_name', '')}",
                site.get('id')
            )
        
        # Set current site if specified
        if self.site_id:
            for i in range(self.site_combo.count()):
                if self.site_combo.itemData(i) == self.site_id:
                    self.site_combo.setCurrentIndex(i)
                    break
    
    def load_years(self):
        """Load available years from find_number (LAG2023, LAG2024, etc.)"""
        finds = self.db_manager.get_finds()
        years = set()
        
        QgsMessageLog.logMessage("DEBUG: Extracting years from find_number", "Statistics", Qgis.Info)
        
        for find in finds:
            find_number = find.get('find_number', '')
            # Extract year from find_number like LAG2023, LAG2024
            if find_number:
                # Look for 4-digit year in the find_number
                import re
                year_match = re.search(r'(\d{4})', find_number)
                if year_match:
                    year = year_match.group(1)
                    years.add(year)
                    if len(years) <= 5:  # Log first few examples
                        QgsMessageLog.logMessage(f"Found year {year} from find_number: {find_number}", 
                                               "Statistics", Qgis.Info)
        
        QgsMessageLog.logMessage(f"Total years found: {sorted(years)}", "Statistics", Qgis.Info)
        
        for year in sorted(years):
            self.year_combo.addItem(year, year)
    
    def load_materials(self):
        """Load available materials and show what's actually in the database"""
        finds = self.db_manager.get_finds()
        materials = {}
        
        # Debug: Log what we find
        QgsMessageLog.logMessage("DEBUG: Checking materials in database", "Statistics", Qgis.Info)
        
        for find in finds:
            # Check both 'material' and 'material_type' fields
            material = find.get('material_type') or find.get('material')
            # Debug log
            if material not in materials:
                QgsMessageLog.logMessage(f"Found material: '{material}' (type: {type(material)})", 
                                       "Statistics", Qgis.Info)
            materials[material] = materials.get(material, 0) + 1
        
        # Log summary
        QgsMessageLog.logMessage(f"Total unique materials: {len(materials)}", "Statistics", Qgis.Info)
        for mat, count in sorted(materials.items(), key=lambda x: x[1], reverse=True)[:10]:
            QgsMessageLog.logMessage(f"  {mat}: {count} finds", "Statistics", Qgis.Info)
        
        # Add to combo box
        for material in sorted(materials.keys()):
            if material and material != 'None' and material != '':
                self.material_combo.addItem(f"{material} ({materials[material]})", material)
    
    def on_site_changed(self):
        """Handle site selection change"""
        self.site_id = self.site_combo.currentData()
        # Reload filters based on new site
        self.load_years()
        self.load_materials()
        self.refresh_data()
    
    def on_filter_changed(self):
        """Handle filter changes"""
        self.filters['year'] = self.year_combo.currentData()
        self.filters['material'] = self.material_combo.currentData()
        self.refresh_data()
    
    def get_filtered_finds(self):
        """Get finds with filters applied"""
        finds = self.db_manager.get_finds(self.site_id)
        
        # Apply year filter based on find_number
        if self.filters.get('year'):
            year = self.filters['year']
            filtered_finds = []
            for f in finds:
                find_number = f.get('find_number', '')
                # Check if year is in find_number (e.g., LAG2023)
                if year in find_number:
                    filtered_finds.append(f)
            finds = filtered_finds
        
        # Apply material filter (check both material_type and material fields)
        if self.filters.get('material'):
            material = self.filters['material']
            finds = [f for f in finds if (f.get('material_type') == material or f.get('material') == material)]
        
        return finds
    
    def refresh_data(self):
        """Refresh statistics and charts"""
        self.update_statistics()
        if MATPLOTLIB_AVAILABLE:
            self.update_chart()
    
    def update_statistics(self):
        """Update statistics display"""
        # Clear existing stats
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get statistics
        stats = self.get_statistics()
        
        # Display statistics in grid
        row = 0
        col = 0
        max_cols = 3
        
        for label, value in stats.items():
            # Create stat widget
            stat_frame = QFrame()
            stat_frame.setFrameStyle(QFrame.Box)
            stat_layout = QVBoxLayout()
            
            # Value
            value_label = QLabel(str(value))
            value_label.setAlignment(Qt.AlignCenter)
            font = value_label.font()
            font.setPointSize(18)
            font.setBold(True)
            value_label.setFont(font)
            stat_layout.addWidget(value_label)
            
            # Label
            label_widget = QLabel(label)
            label_widget.setAlignment(Qt.AlignCenter)
            label_widget.setWordWrap(True)
            stat_layout.addWidget(label_widget)
            
            stat_frame.setLayout(stat_layout)
            self.stats_layout.addWidget(stat_frame, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def get_statistics(self):
        """Get statistics data"""
        stats = {}
        
        # Get filtered finds
        finds = self.get_filtered_finds()
        stats[self.tr("Total Finds")] = len(finds)
        
        if finds:
            # Material distribution
            materials = {}
            for find in finds:
                material = find.get('material_type') or find.get('material') or 'Unknown'
                materials[material] = materials.get(material, 0) + 1
            stats[self.tr("Unique Materials")] = len(materials)
            
            # Most common material
            if materials:
                most_common = max(materials.items(), key=lambda x: x[1])
                stats[self.tr("Most Common Material")] = f"{most_common[0]} ({most_common[1]})"
            
            # Conservation status
            conservation = {}
            for find in finds:
                status = find.get('conservation_status', 'Unknown')
                conservation[status] = conservation.get(status, 0) + 1
            
            # Finds with photos
            with_media = sum(1 for f in finds if f.get('media_count', 0) > 0)
            stats[self.tr("Finds with Media")] = f"{with_media} ({with_media*100//len(finds)}%)"
            
            # Date range
            dates = [f.get('excavation_date') for f in finds if f.get('excavation_date')]
            if dates:
                stats[self.tr("Date Range")] = f"{min(dates)} to {max(dates)}"
            
            # Average depth
            depths = [float(f.get('depth', 0)) for f in finds if f.get('depth')]
            if depths:
                stats[self.tr("Avg Depth")] = f"{sum(depths)/len(depths):.2f} m"
        
        # Add site-specific stats
        if self.site_id:
            # Get dive logs count
            dive_logs = self.db_manager.get_dive_logs(self.site_id)
            stats[self.tr("Total Dives")] = len(dive_logs)
            
            # Get workers count
            workers = set()
            for log in dive_logs:
                # Get team members for this dive
                team = self.db_manager.execute_query(
                    "SELECT worker_id FROM dive_team WHERE dive_id = ?",
                    (log.get('id'),)
                )
                for member in team:
                    worker_id = member.get('worker_id') if isinstance(member, dict) else member[0]
                    workers.add(worker_id)
            stats[self.tr("Team Members")] = len(workers)
        
        return stats
    
    def update_chart(self):
        """Update the chart based on selection"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.figure.clear()
        chart_type = self.chart_combo.currentIndex()
        
        if chart_type == 0:
            self.draw_material_chart()
        elif chart_type == 1:
            self.draw_object_type_chart()
        elif chart_type == 2:
            self.draw_period_chart()
        elif chart_type == 3:
            self.draw_timeline_chart()
        elif chart_type == 4:
            self.draw_depth_chart()
        elif chart_type == 5:
            self.draw_conservation_chart()
        elif chart_type == 6:
            self.draw_category_chart()
        elif chart_type == 7:
            self.draw_material_vs_depth()
        elif chart_type == 8:
            self.draw_material_vs_period()
        
        self.canvas.draw()
    
    def draw_material_chart(self):
        """Draw pie chart of finds by material"""
        ax = self.figure.add_subplot(111)
        
        finds = self.get_filtered_finds()  # Use filtered finds to respect filters
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Debug logging
        QgsMessageLog.logMessage(f"DEBUG draw_material_chart: Processing {len(finds)} finds", "Statistics", Qgis.Info)
        
        # Count materials with detailed logging
        materials = {}
        null_count = 0
        empty_count = 0
        none_count = 0
        
        for i, find in enumerate(finds):
            material = find.get('material_type') or find.get('material')
            
            # Debug first few finds
            if i < 5:
                QgsMessageLog.logMessage(f"Find {i}: material='{material}', type={type(material)}, find_number={find.get('find_number')}", 
                                       "Statistics", Qgis.Info)
            
            # Check different null/empty conditions
            if material is None:
                material = 'Unknown'
                null_count += 1
            elif material == '':
                material = 'Unknown'
                empty_count += 1
            elif material == 'None':
                material = 'Unknown' 
                none_count += 1
            elif not material:
                material = 'Unknown'
            
            materials[material] = materials.get(material, 0) + 1
        
        # Log what we found
        QgsMessageLog.logMessage(f"Material counts: null={null_count}, empty={empty_count}, none_string={none_count}", 
                               "Statistics", Qgis.Info)
        QgsMessageLog.logMessage(f"Material distribution: {materials}", "Statistics", Qgis.Info)
        
        # Create pie chart
        if materials:
            # Limit to top 10 materials, group others
            sorted_materials = sorted(materials.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_materials) > 10:
                top_materials = dict(sorted_materials[:9])
                others = sum(count for _, count in sorted_materials[9:])
                top_materials['Others'] = others
                materials = top_materials
            
            ax.pie(materials.values(), labels=materials.keys(), autopct='%1.1f%%')
            ax.set_title(self.tr('Finds by Material'))
    
    def draw_period_chart(self):
        """Draw bar chart of finds by period"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Count periods
        periods = {}
        for find in finds:
            period = find.get('period', 'Unknown')
            if period:
                periods[period] = periods.get(period, 0) + 1
        
        if periods:
            ax.bar(periods.keys(), periods.values())
            ax.set_xlabel(self.tr('Period'))
            ax.set_ylabel(self.tr('Number of Finds'))
            ax.set_title(self.tr('Finds by Period'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    def draw_timeline_chart(self):
        """Draw timeline of finds by excavation date"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Count finds by date
        dates = {}
        for find in finds:
            date = find.get('excavation_date')
            if date:
                dates[date] = dates.get(date, 0) + 1
        
        if dates:
            sorted_dates = sorted(dates.items())
            ax.plot([d[0] for d in sorted_dates], [d[1] for d in sorted_dates], marker='o')
            ax.set_xlabel(self.tr('Date'))
            ax.set_ylabel(self.tr('Number of Finds'))
            ax.set_title(self.tr('Finds Timeline'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
    
    def draw_depth_chart(self):
        """Draw histogram of depth distribution"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Get depths
        depths = []
        for find in finds:
            depth = find.get('depth')
            if depth:
                try:
                    depths.append(float(depth))
                except (ValueError, TypeError):
                    pass
        
        if depths:
            ax.hist(depths, bins=20, edgecolor='black')
            ax.set_xlabel(self.tr('Depth (m)'))
            ax.set_ylabel(self.tr('Number of Finds'))
            ax.set_title(self.tr('Depth Distribution'))
            ax.grid(True, alpha=0.3)
    
    def draw_conservation_chart(self):
        """Draw donut chart of conservation status"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Count conservation status
        conservation = {}
        for find in finds:
            status = find.get('conservation_status', 'Unknown')
            conservation[status] = conservation.get(status, 0) + 1
        
        if conservation:
            # Create donut chart
            wedges, texts, autotexts = ax.pie(conservation.values(), 
                                              labels=conservation.keys(), 
                                              autopct='%1.1f%%',
                                              wedgeprops=dict(width=0.5))
            ax.set_title(self.tr('Conservation Status'))
    
    def draw_category_chart(self):
        """Draw horizontal bar chart of top categories"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Count categories
        categories = {}
        for find in finds:
            category = find.get('category', 'Unknown')
            if category:
                categories[category] = categories.get(category, 0) + 1
        
        if categories:
            # Get top 15 categories
            sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:15]
            
            ax.barh([c[0] for c in sorted_cats], [c[1] for c in sorted_cats])
            ax.set_xlabel(self.tr('Number of Finds'))
            ax.set_ylabel(self.tr('Category'))
            ax.set_title(self.tr('Top 15 Categories'))
    
    def set_site(self, site_id):
        """Set the current site"""
        self.site_id = site_id
        for i in range(self.site_combo.count()):
            if self.site_combo.itemData(i) == site_id:
                self.site_combo.setCurrentIndex(i)
                break
        self.refresh_data()
    
    def draw_object_type_chart(self):
        """Draw pie chart of finds by object type"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Count object types
        object_types = {}
        for find in finds:
            obj_type = find.get('object_type')
            if not obj_type or obj_type == 'None' or obj_type == '':
                obj_type = 'Unknown'
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
        
        # Create pie chart
        if object_types:
            # Limit to top 10 types, group others
            sorted_types = sorted(object_types.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_types) > 10:
                top_types = dict(sorted_types[:9])
                others = sum(count for _, count in sorted_types[9:])
                top_types['Others'] = others
                object_types = top_types
            
            ax.pie(object_types.values(), labels=object_types.keys(), autopct='%1.1f%%')
            ax.set_title(self.tr('Finds by Object Type'))
    
    def draw_material_vs_depth(self):
        """Draw scatter plot of material vs depth"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Organize data by material
        material_depths = {}
        for find in finds:
            material = find.get('material_type') or find.get('material') or 'Unknown'
            if material == 'None' or material == '':
                material = 'Unknown'
            depth = find.get('depth')
            if depth:
                try:
                    depth_val = float(depth)
                    if material not in material_depths:
                        material_depths[material] = []
                    material_depths[material].append(depth_val)
                except (ValueError, TypeError):
                    pass
        
        if material_depths:
            # Create box plot
            materials = list(material_depths.keys())
            depths_data = [material_depths[m] for m in materials]
            
            ax.boxplot(depths_data, labels=materials)
            ax.set_xlabel(self.tr('Material'))
            ax.set_ylabel(self.tr('Depth (m)'))
            ax.set_title(self.tr('Depth Distribution by Material'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
    
    def draw_material_vs_period(self):
        """Draw heatmap of material vs period"""
        ax = self.figure.add_subplot(111)
        
        finds = self.db_manager.get_finds(self.site_id)
        if not finds:
            ax.text(0.5, 0.5, self.tr('No data available'), 
                   ha='center', va='center')
            return
        
        # Count material-period combinations
        material_period = {}
        materials = set()
        periods = set()
        
        for find in finds:
            material = find.get('material_type') or find.get('material') or 'Unknown'
            if material == 'None' or material == '':
                material = 'Unknown'
            period = find.get('period', 'Unknown')
            
            materials.add(material)
            periods.add(period)
            
            key = (material, period)
            material_period[key] = material_period.get(key, 0) + 1
        
        if material_period:
            # Create matrix
            materials = sorted(list(materials))
            periods = sorted(list(periods))
            
            matrix = []
            for material in materials:
                row = []
                for period in periods:
                    count = material_period.get((material, period), 0)
                    row.append(count)
                matrix.append(row)
            
            # Create heatmap
            im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
            
            # Set ticks
            ax.set_xticks(range(len(periods)))
            ax.set_yticks(range(len(materials)))
            ax.set_xticklabels(periods)
            ax.set_yticklabels(materials)
            
            # Rotate x labels
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # Add colorbar
            plt.colorbar(im, ax=ax)
            
            # Add labels
            ax.set_xlabel(self.tr('Period'))
            ax.set_ylabel(self.tr('Material'))
            ax.set_title(self.tr('Finds Distribution: Material vs Period'))
            
            # Add value annotations
            for i in range(len(materials)):
                for j in range(len(periods)):
                    text = ax.text(j, i, str(matrix[i][j]),
                                 ha="center", va="center", color="black", fontsize=8)
    
    def tr(self, message):
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('StatisticsWidget', message)