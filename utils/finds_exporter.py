#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finds Export Utility for Shipwreck Excavation
Exports finds list and detail sheets with photos in multiple languages
"""

import os
import base64
from datetime import datetime
from qgis.PyQt.QtCore import QObject, QSettings
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtCore import QBuffer, QIODevice

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, 
                                   Paragraph, Spacer, Image, PageBreak,
                                   KeepTogether, Frame, PageTemplate)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class FindsExporter(QObject):
    """Export finds with photos in multiple languages"""
    
    # Translation dictionary
    TRANSLATIONS = {
        'en': {
            'finds_list': 'Finds List',
            'find_details': 'Find Details', 
            'site': 'Site',
            'find_number': 'Find Number',
            'material': 'Material',
            'object_type': 'Object Type',
            'description': 'Description',
            'condition': 'Condition',
            'depth': 'Depth (m)',
            'date': 'Date',
            'finder': 'Finder',
            'location': 'Storage Location',
            'context': 'Context',
            'period': 'Period',
            'quantity': 'Quantity',
            'notes': 'Notes',
            'photos': 'Photos',
            'no_photo': 'No photo available',
            'generated': 'Generated',
            'page': 'Page',
            'of': 'of',
            'total_finds': 'Total Finds',
            'summary': 'Summary',
            'ceramic': 'Ceramic',
            'metal': 'Metal', 
            'glass': 'Glass',
            'wood': 'Wood',
            'stone': 'Stone',
            'other': 'Other'
        },
        'id': {
            'finds_list': 'Daftar Temuan',
            'find_details': 'Detail Temuan',
            'site': 'Situs',
            'find_number': 'Nomor Temuan',
            'material': 'Material',
            'object_type': 'Jenis Objek',
            'description': 'Deskripsi',
            'condition': 'Kondisi',
            'depth': 'Kedalaman (m)',
            'date': 'Tanggal',
            'finder': 'Penemu',
            'location': 'Lokasi Penyimpanan',
            'context': 'Konteks',
            'period': 'Periode',
            'quantity': 'Jumlah',
            'notes': 'Catatan',
            'photos': 'Foto',
            'no_photo': 'Tidak ada foto',
            'generated': 'Dibuat',
            'page': 'Halaman',
            'of': 'dari',
            'total_finds': 'Total Temuan',
            'summary': 'Ringkasan',
            'ceramic': 'Keramik',
            'metal': 'Logam',
            'glass': 'Kaca',
            'wood': 'Kayu',
            'stone': 'Batu',
            'other': 'Lainnya'
        }
    }
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_lang = 'en'
        
    def set_language(self, lang_code):
        """Set export language"""
        if lang_code in self.TRANSLATIONS:
            self.current_lang = lang_code
        else:
            self.current_lang = 'en'
    
    def tr(self, key):
        """Translate key to current language"""
        return self.TRANSLATIONS.get(self.current_lang, {}).get(key, key)
    
    def get_image_data(self, file_path):
        """Convert image to base64 for embedding in HTML"""
        if not file_path or not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode()
                # Determine MIME type
                ext = os.path.splitext(file_path)[1].lower()
                mime_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp'
                }.get(ext, 'image/jpeg')
                
                return f"data:{mime_type};base64,{image_data}"
        except:
            return None
    
    def export_finds_list_html(self, site_id, output_path, include_photos=True):
        """Export finds list to HTML with embedded images"""
        # Get finds data
        finds = self.db_manager.execute_query(
            "SELECT * FROM finds WHERE site_id = ? ORDER BY find_number",
            (site_id,)
        )
        
        if not finds:
            return False
        
        # Get site info
        site = self.db_manager.execute_query("SELECT * FROM sites WHERE id = ?", (site_id,))[0]
        site_name = site['site_name'] if isinstance(site, dict) else site[3]
        
        # Get photo count for each find
        photo_counts = {}
        for find in finds:
            find_id = find['id'] if isinstance(find, dict) else find[0]
            relations = self.db_manager.execute_query(
                "SELECT COUNT(*) as count FROM media_relations WHERE related_type = 'find' AND related_id = ?",
                (find_id,)
            )
            if relations:
                photo_counts[find_id] = relations[0].get('count', 0) if isinstance(relations[0], dict) else 0
        
        # Start HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.tr('finds_list')} - {site_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .photo-cell {{
            text-align: center;
        }}
        .photo-cell img {{
            max-width: 100px;
            max-height: 100px;
            margin: 2px;
        }}
        .no-photo {{
            color: #999;
            font-style: italic;
        }}
        .summary {{
            background: #ecf0f1;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>{self.tr('finds_list')} - {site_name}</h1>
    <p>{self.tr('generated')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
"""
        
        # Summary statistics
        material_counts = {}
        for find in finds:
            material = find['material_type'] if isinstance(find, dict) else find[4]  # material_type is at index 4
            material_counts[material] = material_counts.get(material, 0) + 1
        
        html += f'<div class="summary">'
        html += f'<h3>{self.tr("summary")}</h3>'
        html += f'<p><strong>{self.tr("total_finds")}:</strong> {len(finds)}</p>'
        for material, count in sorted(material_counts.items()):
            material_tr = self.tr(material.lower()) if material else self.tr('other')
            html += f'<p>{material_tr}: {count}</p>'
        html += '</div>'
        
        # Finds table
        html += '<table>'
        html += '<thead><tr>'
        html += f'<th>{self.tr("find_number")}</th>'
        html += f'<th>{self.tr("material")}</th>'
        html += f'<th>{self.tr("object_type")}</th>'
        html += f'<th>{self.tr("description")}</th>'
        html += f'<th>{self.tr("condition")}</th>'
        html += f'<th>{self.tr("date")}</th>'
        if include_photos:
            html += f'<th>{self.tr("photos")}</th>'
        html += '</tr></thead><tbody>'
        
        for find in finds:
            # Extract data
            if isinstance(find, dict):
                find_id = find['id']
                find_number = find['find_number']
                material = find['material_type']
                object_type = find['object_type']
                description = find['description']
                condition = find['condition']
                find_date = find['find_date']
                photo_count = photo_counts.get(find_id, 0)
            else:
                find_id = find[0]
                find_number = find[3]  # find_number is at index 3
                material = find[4]     # material_type is at index 4
                object_type = find[5]  # object_type is at index 5
                description = find[6]  # description is at index 6
                condition = find[7]    # condition is at index 7
                find_date = find[16]   # find_date is at index 16
                photo_count = find[-1] # photo_count is last
            
            html += '<tr>'
            html += f'<td><strong>{find_number}</strong></td>'
            html += f'<td>{material or "-"}</td>'
            html += f'<td>{object_type or "-"}</td>'
            html += f'<td>{description or "-"}</td>'
            html += f'<td>{condition or "-"}</td>'
            html += f'<td>{find_date or "-"}</td>'
            
            if include_photos:
                html += '<td class="photo-cell">'
                
                if photo_count > 0:
                    # Get first photo for preview
                    photo_query = """
                        SELECT m.file_path FROM media m
                        JOIN media_relations mr ON m.id = mr.media_id
                        WHERE mr.related_type = 'find' AND mr.related_id = ?
                        AND m.media_type = 'photo'
                        LIMIT 1
                    """
                    photos = self.db_manager.execute_query(photo_query, (find_id,))
                    
                    if photos:
                        photo_path = photos[0]['file_path'] if isinstance(photos[0], dict) else photos[0][0]
                        
                        if photo_path:  # Check if photo_path is not None
                            # Convert relative path to absolute if needed
                            if not os.path.isabs(photo_path):
                                # Try with configured media base path from settings
                                settings = QSettings('ShipwreckExcavation', 'ShipwreckExcavation')
                                media_base_path = settings.value('media_base_path', '')
                                if media_base_path:
                                    full_path = os.path.join(media_base_path, photo_path)
                                else:
                                    full_path = None

                                if full_path and os.path.exists(full_path):
                                    photo_path = full_path
                                elif os.path.exists(photo_path):
                                    # Use as is if it exists relative to current directory
                                    pass
                            
                            # Try thumbnail first
                            thumb_path = self.get_thumbnail_path(photo_path)
                            if thumb_path and os.path.exists(thumb_path):
                                img_data = self.get_image_data(thumb_path)
                            else:
                                img_data = self.get_image_data(photo_path)
                        else:
                            img_data = None
                        
                        if img_data:
                            html += f'<img src="{img_data}" alt="{find_number}">'
                            if photo_count > 1:
                                html += f'<br><small>(+{photo_count-1} more)</small>'
                        else:
                            html += f'<span class="no-photo">{self.tr("no_photo")}</span>'
                else:
                    html += f'<span class="no-photo">{self.tr("no_photo")}</span>'
                    
                html += '</td>'
            
            html += '</tr>'
        
        html += '</tbody></table>'
        
        html += f'<div class="footer">'
        html += f'{self.tr("generated")}: {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        html += '</div>'
        
        html += '</body></html>'
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return True
    
    def export_finds_list_pdf(self, site_id, output_path, include_photos=True):
        """Export finds list to PDF with photos"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is not installed")
        
        # Get finds data
        finds = self.db_manager.execute_query(
            "SELECT * FROM finds WHERE site_id = ? ORDER BY find_number",
            (site_id,)
        )
        
        # Get photo count for each find
        photo_counts = {}
        for find in finds:
            find_id = find['id'] if isinstance(find, dict) else find[0]
            relations = self.db_manager.execute_query(
                "SELECT COUNT(*) as count FROM media_relations WHERE related_type = 'find' AND related_id = ?",
                (find_id,)
            )
            if relations:
                photo_counts[find_id] = relations[0].get('count', 0) if isinstance(relations[0], dict) else 0
        
        if not finds:
            return False
        
        # Get site info
        site = self.db_manager.execute_query("SELECT * FROM sites WHERE id = ?", (site_id,))[0]
        site_name = site['site_name'] if isinstance(site, dict) else site[2]
        
        # Create PDF
        doc = SimpleDocTemplate(output_path, pagesize=A4 if not include_photos else landscape(A4),
                              rightMargin=15*mm, leftMargin=15*mm,
                              topMargin=15*mm, bottomMargin=15*mm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Title
        elements.append(Paragraph(f"{self.tr('finds_list')} - {site_name}", title_style))
        elements.append(Paragraph(f"{self.tr('generated')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                                styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Summary
        material_counts = {}
        for find in finds:
            material = find['material_type'] if isinstance(find, dict) else find[4]  # material_type is at index 4
            material_counts[material] = material_counts.get(material, 0) + 1
        
        summary_data = [[self.tr('summary'), '']]
        summary_data.append([self.tr('total_finds'), str(len(finds))])
        for material, count in sorted(material_counts.items()):
            material_tr = self.tr(material.lower()) if material else self.tr('other')
            summary_data.append([material_tr, str(count)])
        
        summary_table = Table(summary_data, colWidths=[100*mm, 50*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Finds table
        if include_photos:
            # Table with photos - use landscape
            headers = [self.tr('find_number'), self.tr('material'), self.tr('object_type'),
                      self.tr('description'), self.tr('photos')]
            col_widths = [40*mm, 35*mm, 35*mm, 80*mm, 60*mm]
        else:
            # Table without photos - portrait
            headers = [self.tr('find_number'), self.tr('material'), self.tr('object_type'),
                      self.tr('description'), self.tr('condition'), self.tr('date')]
            col_widths = [30*mm, 30*mm, 30*mm, 60*mm, 25*mm, 25*mm]
        
        data = [headers]
        
        for find in finds:
            # Extract data
            if isinstance(find, dict):
                find_id = find['id']
                find_number = find['find_number']
                material = find['material_type']
                object_type = find['object_type']
                description = find['description']
                condition = find['condition']
                find_date = find['find_date']
                photo_count = photo_counts.get(find_id, 0)
            else:
                find_id = find[0]
                find_number = find[3]  # find_number is at index 3
                material = find[4]     # material_type is at index 4
                object_type = find[5]  # object_type is at index 5
                description = find[6]  # description is at index 6
                condition = find[7]    # condition is at index 7
                find_date = find[16]   # find_date is at index 16
                photo_count = find[-1] # photo_count is last
            
            row = [
                Paragraph(f"<b>{find_number}</b>", styles['Normal']),
                Paragraph(material or "-", styles['Normal']),
                Paragraph(object_type or "-", styles['Normal']),
                Paragraph(description or "-", styles['Normal'])
            ]
            
            if include_photos:
                # Add photo
                if photo_count > 0:
                    photo_query = """
                        SELECT m.file_path FROM media m
                        JOIN media_relations mr ON m.id = mr.media_id
                        WHERE mr.related_type = 'find' AND mr.related_id = ?
                        AND m.media_type = 'photo'
                        LIMIT 1
                    """
                    photos = self.db_manager.execute_query(photo_query, (find_id,))
                    
                    if photos:
                        photo_path = photos[0]['file_path'] if isinstance(photos[0], dict) else photos[0][0]
                        
                        img_path = None
                        if photo_path:  # Check if photo_path is not None
                            # Convert relative path to absolute if needed
                            if not os.path.isabs(photo_path):
                                # Try with configured media base path from settings
                                settings = QSettings('ShipwreckExcavation', 'ShipwreckExcavation')
                                media_base_path = settings.value('media_base_path', '')
                                if media_base_path:
                                    full_path = os.path.join(media_base_path, photo_path)
                                else:
                                    full_path = None

                                if full_path and os.path.exists(full_path):
                                    photo_path = full_path
                                elif os.path.exists(photo_path):
                                    # Use as is if it exists relative to current directory
                                    pass
                            
                            # Try thumbnail first
                            thumb_path = self.get_thumbnail_path(photo_path)
                            img_path = thumb_path if thumb_path and os.path.exists(thumb_path) else photo_path
                        
                        if img_path and os.path.exists(img_path):
                            try:
                                img = Image(img_path, width=50*mm, height=50*mm, kind='proportional')
                                if photo_count > 1:
                                    cell_content = [img, Paragraph(f"<i>(+{photo_count-1} more)</i>", 
                                                                 styles['Normal'])]
                                    row.append(cell_content)
                                else:
                                    row.append(img)
                            except:
                                row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
                        else:
                            row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
                    else:
                        row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
                else:
                    row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
            else:
                # Add condition and date
                row.extend([
                    Paragraph(condition or "-", styles['Normal']),
                    Paragraph(str(find_date)[:10] if find_date else "-", styles['Normal'])
                ])
            
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')])
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        return True
    
    def export_find_details_pdf(self, find_id, output_path):
        """Export individual find detail sheet with all photos"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is not installed")
        
        # Get find data
        find_data = self.db_manager.execute_query(
            "SELECT * FROM finds WHERE id = ?", (find_id,)
        )
        
        if not find_data:
            return False
        
        find = find_data[0]
        
        # Get site name
        site_data = self.db_manager.execute_query(
            "SELECT site_name FROM sites WHERE id = ?", 
            (find['site_id'] if isinstance(find, dict) else find[1],)
        )
        site_name = site_data[0]['site_name'] if site_data and isinstance(site_data[0], dict) else site_data[0][0] if site_data else "Unknown"
        
        # Get photos
        relations = self.db_manager.execute_query(
            "SELECT media_id FROM media_relations WHERE related_type = 'find' AND related_id = ?",
            (find_id,)
        )
        
        photos = []
        if relations:
            for rel in relations:
                media_id = rel['media_id'] if isinstance(rel, dict) else rel[0]
                media_result = self.db_manager.execute_query(
                    "SELECT file_path, description FROM media WHERE id = ? AND media_type = 'photo'",
                    (media_id,)
                )
                if media_result:
                    photos.extend(media_result)
        
        # Create PDF
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                              rightMargin=15*mm, leftMargin=15*mm,
                              topMargin=15*mm, bottomMargin=15*mm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        find_number = find['find_number'] if isinstance(find, dict) else find[3]
        
        elements.append(Paragraph(f"{self.tr('find_details')}: {find_number}", title_style))
        elements.append(Spacer(1, 20))
        
        # Details table
        details_data = []
        
        # Add all find fields
        fields = [
            ('site', site_name),
            ('find_number', find_number),
            ('material', find.get('material_type', '') if isinstance(find, dict) else ''),
            ('object_type', find.get('object_type', '') if isinstance(find, dict) else ''),
            ('description', find.get('description', '') if isinstance(find, dict) else ''),
            ('condition', find.get('condition', '') if isinstance(find, dict) else ''),
            ('depth', find.get('depth', '') if isinstance(find, dict) else ''),
            ('date', find.get('find_date', '') if isinstance(find, dict) else ''),
            ('finder', find.get('created_by', find.get('telegram_user', 'Unknown')) if isinstance(find, dict) else 'Unknown')
        ]
        
        for field_key, value in fields:
            if value:
                details_data.append([
                    Paragraph(f"<b>{self.tr(field_key)}:</b>", styles['Normal']),
                    Paragraph(str(value), styles['Normal'])
                ])
        
        details_table = Table(details_data, colWidths=[50*mm, 120*mm])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(details_table)
        elements.append(Spacer(1, 30))
        
        # Photos section
        if photos:
            elements.append(Paragraph(f"{self.tr('photos')} ({len(photos)})", styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            # Add photos in a grid
            photo_data = []
            row = []
            
            for i, photo in enumerate(photos):
                photo_path = photo['file_path'] if isinstance(photo, dict) else photo[0]
                caption = photo['description'] if isinstance(photo, dict) else photo[1]
                
                if photo_path:  # Check if photo_path is not None
                    # Convert relative path to absolute if needed
                    if not os.path.isabs(photo_path):
                        # Try with configured media base path from settings
                        settings = QSettings('ShipwreckExcavation', 'ShipwreckExcavation')
                        media_base_path = settings.value('media_base_path', '')
                        if media_base_path:
                            full_path = os.path.join(media_base_path, photo_path)
                        else:
                            full_path = None

                        if full_path and os.path.exists(full_path):
                            photo_path = full_path
                        elif os.path.exists(photo_path):
                            # Use as is if it exists relative to current directory
                            pass
                    
                    # Try thumbnail first
                    thumb_path = self.get_thumbnail_path(photo_path)
                    img_path = thumb_path if thumb_path and os.path.exists(thumb_path) else photo_path
                    
                    if img_path and os.path.exists(img_path):
                        try:
                            img = Image(img_path, width=80*mm, height=80*mm, kind='proportional')
                            cell_content = [img]
                            if caption:
                                cell_content.append(Paragraph(f"<i>{caption}</i>", styles['Normal']))
                            row.append(cell_content)
                        except:
                            row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
                    else:
                        row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
                else:
                    row.append(Paragraph(self.tr('no_photo'), styles['Normal']))
                
                # Start new row after 2 photos
                if len(row) == 2 or i == len(photos) - 1:
                    while len(row) < 2:
                        row.append("")
                    photo_data.append(row)
                    row = []
            
            if photo_data:
                photo_table = Table(photo_data, colWidths=[85*mm, 85*mm])
                photo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                elements.append(photo_table)
        else:
            elements.append(Paragraph(self.tr('no_photo'), styles['Normal']))
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(f"{self.tr('generated')}: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                                styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        return True
    
    def get_thumbnail_path(self, image_path):
        """Get thumbnail path for an image"""
        if not image_path:
            return None
            
        # Try different thumbnail locations
        try:
            filename = os.path.basename(image_path)
            base_dir = os.path.dirname(image_path)
        except (TypeError, AttributeError):
            return None
        
        # Check common thumbnail locations
        possible_paths = [
            os.path.join(base_dir, '..', 'thumbnails', f'thumb_{filename}'),
            os.path.join(base_dir, 'thumbnails', f'thumb_{filename}'),
            os.path.join(os.path.dirname(base_dir), 'thumbnails', f'thumb_{filename}')
        ]
        
        for path in possible_paths:
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                return normalized_path
        
        return None