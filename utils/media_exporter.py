#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Media Export Utility for Shipwreck Excavation
Exports media list with thumbnails to HTML or PDF
"""

import os
from datetime import datetime
from qgis.PyQt.QtCore import QObject

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class MediaExporter(QObject):
    """Export media lists with thumbnails"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
    def export_to_html(self, site_id, output_path):
        """Export media list to HTML with thumbnails"""
        # Get media for site
        query = """
            SELECT m.*, mr.related_type, mr.related_id,
                   CASE 
                       WHEN mr.related_type = 'site' THEN s.site_name
                       WHEN mr.related_type = 'find' THEN f.find_number
                       WHEN mr.related_type = 'dive' THEN d.dive_number
                   END as related_name
            FROM media m
            JOIN media_relations mr ON m.id = mr.media_id
            LEFT JOIN sites s ON mr.related_type = 'site' AND mr.related_id = s.id
            LEFT JOIN finds f ON mr.related_type = 'find' AND mr.related_id = f.id
            LEFT JOIN dive_logs d ON mr.related_type = 'dive' AND mr.related_id = d.id
            WHERE mr.related_id IN (
                SELECT id FROM sites WHERE id = ?
                UNION
                SELECT id FROM finds WHERE site_id = ?
                UNION
                SELECT id FROM dive_logs WHERE site_id = ?
            )
            ORDER BY m.media_type, m.created_at DESC
        """
        
        media_files = self.db_manager.execute_query(query, (site_id, site_id, site_id))
        
        if not media_files:
            return False
        
        # Get site info
        site = self.db_manager.execute_query("SELECT * FROM sites WHERE id = ?", (site_id,))[0]
        site_name = site['site_name'] if isinstance(site, dict) else site[2]
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Media List - {site_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        .media-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .media-item {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
            background: #f9f9f9;
        }}
        .media-item img {{
            max-width: 180px;
            max-height: 180px;
            margin-bottom: 10px;
        }}
        .media-info {{
            font-size: 12px;
            text-align: left;
        }}
        .media-type {{
            font-weight: bold;
            color: #666;
        }}
        .no-thumbnail {{
            width: 180px;
            height: 180px;
            background: #eee;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            margin: 0 auto 10px;
        }}
        .section {{
            margin-top: 30px;
        }}
        .stats {{
            background: #f0f0f0;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <h1>Media List - {site_name}</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
"""
        
        # Group media by type
        media_by_type = {}
        for media in media_files:
            if isinstance(media, dict):
                media_type = media.get('media_type', 'photo')  # Default to photo if missing
            else:
                media_type = media[1] if len(media) > 1 else 'photo'
            
            if media_type not in media_by_type:
                media_by_type[media_type] = []
            media_by_type[media_type].append(media)
        
        # Statistics
        html += '<div class="stats">'
        html += f'<h3>Summary</h3>'
        for media_type, items in media_by_type.items():
            html += f'<p>{media_type.title()}: {len(items)} files</p>'
        html += f'<p><strong>Total: {len(media_files)} files</strong></p>'
        html += '</div>'
        
        # Media sections
        for media_type, items in media_by_type.items():
            html += f'<div class="section">'
            html += f'<h2>{media_type.title()}s ({len(items)})</h2>'
            html += '<div class="media-grid">'
            
            for media in items:
                # Extract data with safe defaults
                if isinstance(media, dict):
                    filename = media.get('file_name', 'Unknown')
                    file_path = media.get('file_path', '')
                    file_size = media.get('file_size', 0)
                    description = media.get('description', '')
                    capture_date = media.get('capture_date', '')
                    related_type = media.get('related_type', '')
                    related_name = media.get('related_name', '')
                else:
                    filename = media[2]
                    file_path = media[3]
                    file_size = media[4]
                    description = media[6]
                    capture_date = media[8]
                    related_type = media[11] if len(media) > 11 else ''
                    related_name = media[13] if len(media) > 13 else ''
                
                html += '<div class="media-item">'
                
                # Thumbnail or placeholder
                if media_type == 'photo':
                    # Try to find thumbnail
                    thumb_filename = f"thumb_{filename}"
                    thumb_path = os.path.join(os.path.dirname(file_path), '..', 'thumbnails', thumb_filename)
                    
                    if os.path.exists(thumb_path):
                        # Convert to relative path for HTML
                        rel_path = os.path.relpath(thumb_path, os.path.dirname(output_path))
                        html += f'<img src="{rel_path}" alt="{filename}">'
                    elif os.path.exists(file_path):
                        # Use original if no thumbnail
                        rel_path = os.path.relpath(file_path, os.path.dirname(output_path))
                        html += f'<img src="{rel_path}" alt="{filename}">'
                    else:
                        html += '<div class="no-thumbnail">No Image</div>'
                else:
                    # Placeholder for non-images
                    icon = "📹" if media_type == "video" else "📄"
                    html += f'<div class="no-thumbnail">{icon}<br>{media_type}</div>'
                
                # Media info
                html += '<div class="media-info">'
                html += f'<div class="media-type">{filename}</div>'
                
                if file_size:
                    if file_size > 1024*1024:
                        size_str = f"{file_size/(1024*1024):.1f} MB"
                    else:
                        size_str = f"{file_size/1024:.1f} KB"
                    html += f'<div>Size: {size_str}</div>'
                
                if related_type and related_name:
                    html += f'<div>Associated: {related_type} - {related_name}</div>'
                
                if capture_date:
                    html += f'<div>Date: {str(capture_date)[:10]}</div>'
                
                if description:
                    html += f'<div style="margin-top:5px; font-style:italic">{description[:100]}</div>'
                
                html += '</div></div>'
            
            html += '</div></div>'
        
        html += '</body></html>'
        
        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return True
    
    def export_to_pdf(self, site_id, output_path):
        """Export media list to PDF with thumbnails"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is not installed")
            
        # Get media files
        query = """
            SELECT m.*, mr.related_type, mr.related_id,
                   CASE 
                       WHEN mr.related_type = 'site' THEN s.site_name
                       WHEN mr.related_type = 'find' THEN f.find_number
                       WHEN mr.related_type = 'dive' THEN d.dive_number
                   END as related_name
            FROM media m
            JOIN media_relations mr ON m.id = mr.media_id
            LEFT JOIN sites s ON mr.related_type = 'site' AND mr.related_id = s.id
            LEFT JOIN finds f ON mr.related_type = 'find' AND mr.related_id = f.id
            LEFT JOIN dive_logs d ON mr.related_type = 'dive' AND mr.related_id = d.id
            WHERE mr.related_id IN (
                SELECT id FROM sites WHERE id = ?
                UNION
                SELECT id FROM finds WHERE site_id = ?
                UNION
                SELECT id FROM dive_logs WHERE site_id = ?
            )
            ORDER BY m.media_type, m.created_at DESC
        """
        
        media_files = self.db_manager.execute_query(query, (site_id, site_id, site_id))
        
        if not media_files:
            return False
        
        # Get site info
        site = self.db_manager.execute_query("SELECT * FROM sites WHERE id = ?", (site_id,))[0]
        site_name = site['site_name'] if isinstance(site, dict) else site[2]
        
        # Create PDF
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4),
                              rightMargin=15*mm, leftMargin=15*mm,
                              topMargin=15*mm, bottomMargin=15*mm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#000000'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph(f"Media List - {site_name}", title_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Group by type
        media_by_type = {}
        for media in media_files:
            media_type = media.get('media_type', 'photo') if isinstance(media, dict) else (media[1] if len(media) > 1 else 'photo')
            if media_type not in media_by_type:
                media_by_type[media_type] = []
            media_by_type[media_type].append(media)
        
        # Process each type
        for media_type, items in media_by_type.items():
            elements.append(Paragraph(f"{media_type.title()}s ({len(items)})", styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            # Create table for this type
            data = []
            row = []
            
            for i, media in enumerate(items):
                # Extract data with safe defaults
                if isinstance(media, dict):
                    filename = media.get('file_name', 'Unknown')
                    file_path = media.get('file_path', '')
                    related_type = media.get('related_type', '')
                    related_name = media.get('related_name', '')
                else:
                    filename = media[2]
                    file_path = media[3]
                    related_type = media[11] if len(media) > 11 else ''
                    related_name = media[13] if len(media) > 13 else ''
                
                # Create cell content
                cell_content = []
                
                # Add thumbnail for photos
                if media_type == 'photo':
                    # Find thumbnail or use original
                    thumb_path = self.get_thumbnail_path(file_path)
                    
                    # Try thumbnail first, then original
                    img_path = thumb_path if thumb_path and os.path.exists(thumb_path) else file_path
                    
                    if os.path.exists(img_path):
                        try:
                            img = Image(img_path, width=60*mm, height=60*mm, kind='proportional')
                            cell_content.append(img)
                        except Exception as e:
                            # If image fails, try original file
                            if img_path != file_path and os.path.exists(file_path):
                                try:
                                    img = Image(file_path, width=60*mm, height=60*mm, kind='proportional')
                                    cell_content.append(img)
                                except:
                                    cell_content.append(Paragraph("[Image Error]", styles['Normal']))
                            else:
                                cell_content.append(Paragraph("[Image Error]", styles['Normal']))
                    else:
                        cell_content.append(Paragraph("[File Not Found]", styles['Normal']))
                else:
                    cell_content.append(Paragraph(f"[{media_type}]", styles['Normal']))
                
                # Add filename and info
                info = f"<b>{filename}</b><br/>"
                if related_type and related_name:
                    info += f"{related_type}: {related_name}"
                
                cell_content.append(Paragraph(info, styles['Normal']))
                
                row.append(cell_content)
                
                # Start new row after 3 items
                if len(row) == 3 or i == len(items) - 1:
                    # Pad row if needed
                    while len(row) < 3:
                        row.append("")
                    data.append(row)
                    row = []
            
            if data:
                table = Table(data, colWidths=[90*mm, 90*mm, 90*mm])
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]))
                
                elements.append(table)
                elements.append(PageBreak())
        
        # Build PDF
        doc.build(elements)
        
        return True
    
    def get_thumbnail_path(self, image_path):
        """Get thumbnail path for an image"""
        if not image_path:
            return None
            
        filename = os.path.basename(image_path)
        base_dir = os.path.dirname(image_path)
        
        # Check different possible thumbnail locations
        possible_paths = [
            os.path.join(base_dir, '..', 'thumbnails', f'thumb_{filename}'),
            os.path.join(base_dir, 'thumbnails', f'thumb_{filename}'),
            os.path.join(os.path.dirname(base_dir), 'thumbnails', f'thumb_{filename}'),
            # Also check without 'thumb_' prefix
            os.path.join(base_dir, '..', 'thumbnails', filename),
            os.path.join(os.path.dirname(base_dir), 'thumbnails', filename)
        ]
        
        for path in possible_paths:
            normalized_path = os.path.normpath(path)
            if os.path.exists(normalized_path):
                return normalized_path
        
        return None