#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dive Log Report Generator for QGIS Plugin
Generates PDF dive log sheets with signature information
"""

import os
from datetime import datetime
from qgis.PyQt.QtCore import QObject

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import qrcode
    from io import BytesIO
    import json
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class DiveLogReportGenerator(QObject):
    """Generate PDF dive log reports"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
    def is_available(self):
        """Check if report generation is available"""
        return REPORTLAB_AVAILABLE
    
    def generate_dive_sheet(self, dive_id, output_path):
        """Generate a dive log sheet with signature information"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is not installed. Please install it with: pip install reportlab qrcode")
            
        # Get dive information
        dive_logs = self.db_manager.execute_query(
            "SELECT * FROM dive_logs WHERE id = ?",
            (dive_id,)
        )
        
        if not dive_logs:
            return None
            
        dive = dive_logs[0]
        
        # Get site information
        sites = self.db_manager.execute_query(
            "SELECT * FROM sites WHERE id = ?",
            (dive['site_id'] if isinstance(dive, dict) else dive[1],)
        )
        
        if sites:
            site = sites[0]
            # Add site info to dive data
            if isinstance(dive, dict):
                dive['site_name'] = site['site_name'] if isinstance(site, dict) else site[3]
                dive['site_code'] = site['site_code'] if isinstance(site, dict) else site[2]
            else:
                # Convert to dict for easier handling
                dive_dict = {
                    'id': dive[0],
                    'site_id': dive[1],
                    'dive_number': dive[2],
                    'dive_date': dive[3],
                    'dive_start': dive[4],
                    'dive_end': dive[5],
                    'max_depth': dive[6],
                    'avg_depth': dive[7] if len(dive) > 7 else None,
                    'site_name': site['site_name'] if isinstance(site, dict) else site[3],
                    'site_code': site['site_code'] if isinstance(site, dict) else site[2]
                }
                dive = dive_dict
        
        # Get team members
        team_members = self.db_manager.execute_query(
            "SELECT * FROM dive_team WHERE dive_id = ?",
            (dive_id,)
        )
        
        # Get worker details and signatures for each team member
        team = []
        for member in team_members or []:
            worker_id = member['worker_id'] if isinstance(member, dict) else member[1]
            
            # Get worker details
            workers = self.db_manager.execute_query(
                "SELECT * FROM workers WHERE id = ?",
                (worker_id,)
            )
            
            if workers:
                worker = workers[0]
                
                # Get signature for this worker and dive log
                print(f"DEBUG: Looking for signature for dive_log_id={dive_id}, worker_id={worker_id}")
                signatures = self.db_manager.execute_query(
                    "SELECT * FROM dive_log_signatures WHERE dive_log_id = ? AND worker_id = ?",
                    (dive_id, worker_id)
                )
                print(f"DEBUG: Found signatures: {signatures}")
                
                signature_hash = None
                signature_timestamp = None
                if signatures:
                    sig = signatures[0]
                    signature_hash = sig.get('signature_hash') if isinstance(sig, dict) else None
                    signature_timestamp = sig.get('created_at') if isinstance(sig, dict) else None
                
                # Build team member data
                team_data = {
                    'worker_id': worker_id,
                    'role': member['role'] if isinstance(member, dict) else member[4],
                    'full_name': worker['full_name'] if isinstance(worker, dict) else worker[3],
                    'worker_code': worker['worker_code'] if isinstance(worker, dict) else worker[2],
                    'dive_certification': worker.get('dive_certification', '') if isinstance(worker, dict) else '',
                    'bottom_time': None,  # These fields don't exist in the current schema
                    'decompression_time': None,
                    'air_consumed': None,
                    'signature_hash': signature_hash,
                    'signature_timestamp': signature_timestamp,
                    'telegram_username': worker.get('telegram_username') if isinstance(worker, dict) else None
                }
                team.append(team_data)
        
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
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=10,
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph("DIVE LOG SHEET", title_style))
        elements.append(Spacer(1, 10*mm))
        
        # Dive site info header  
        site_name = dive['site_name'] if isinstance(dive, dict) else dive[10]
        site_code = dive['site_code'] if isinstance(dive, dict) else dive[11]
        dive_date = dive['dive_date'] if isinstance(dive, dict) else dive[3]
        dive_number = dive['dive_number'] if isinstance(dive, dict) else dive[2]
        
        header_data = [
            ['Dive Site:', site_name, '', 'Site Code:', site_code],
            ['Date:', dive_date, '', 'Dive Nr:', dive_number]
        ]
        
        header_table = Table(header_data, colWidths=[25*mm, 55*mm, 20*mm, 25*mm, 55*mm])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 5*mm))
        
        # Extract dive info
        dive_start = dive['dive_start'] if isinstance(dive, dict) else dive[4]
        dive_end = dive['dive_end'] if isinstance(dive, dict) else dive[5]
        max_depth = dive['max_depth'] if isinstance(dive, dict) else dive[6]
        avg_depth = dive['avg_depth'] if isinstance(dive, dict) else dive[7]
        water_temp = dive['water_temp'] if isinstance(dive, dict) else dive[8]
        visibility = dive['visibility'] if isinstance(dive, dict) else dive[9]
        
        # Dive information
        info_data = [
            ['Start Time:', dive_start or '', 'End Time:', dive_end or ''],
            ['Max Depth:', f"{max_depth}m" if max_depth else "", 'Avg Depth:', f"{avg_depth}m" if avg_depth else ""],
            ['Water Temp:', f"{water_temp}°C" if water_temp else "", 'Visibility:', f"{visibility}m" if visibility else ""]
        ]
        
        info_table = Table(info_data, colWidths=[25*mm, 65*mm, 25*mm, 65*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 10*mm))
        
        # Team members table with signature status
        team_header = ['Name', 'Role', 'Bottom Time', 'Deco Time', 'Air (BAR)', 'Signature']
        team_data = [team_header]
        
        for member in team:
            # Extract member data
            if isinstance(member, dict):
                full_name = member['full_name']
                role = member['role'] or ""
                bottom_time = member['bottom_time']
                decompression_time = member['decompression_time']
                air_consumed = member['air_consumed']
                signature_hash = member['signature_hash']
                signature_timestamp = member['signature_timestamp']
            else:
                full_name = member[5]  # Adjust indices based on query
                role = member[3] or ""
                bottom_time = member[4]
                decompression_time = member[5]
                air_consumed = member[6]
                signature_hash = member[8] if len(member) > 8 else None
                signature_timestamp = member[9] if len(member) > 9 else None
            
            # Signature field
            if signature_hash:
                signature_text = f"✓ Signed\n{signature_timestamp[:10] if signature_timestamp else ''}"
            else:
                signature_text = "Pending"
            
            team_data.append([
                full_name,
                role,
                f"{bottom_time} min" if bottom_time else "",
                f"{decompression_time} min" if decompression_time else "",
                str(air_consumed) if air_consumed else "",
                signature_text
            ])
        
        # Add empty rows
        for i in range(max(5 - len(team), 0)):
            team_data.append(["", "", "", "", "", ""])
        
        team_table = Table(team_data, colWidths=[40*mm, 30*mm, 25*mm, 25*mm, 20*mm, 30*mm])
        team_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (2, 0), (4, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('ROWHEIGHTS', (0, 1), (-1, -1), 15*mm),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        
        elements.append(Paragraph("Dive Team", styles['Heading2']))
        elements.append(Spacer(1, 5*mm))
        elements.append(team_table)
        
        # Build PDF
        doc.build(elements)
        
        return output_path