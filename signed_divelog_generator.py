#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signed Dive Log Generator
Generates dive log sheets with digital signature information
"""

import sqlite3
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode
from io import BytesIO
import json

class SignedDiveLogGenerator:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        
    def generate_signed_dive_sheet(self, dive_id, output_path):
        """Generate a dive log sheet with signature information"""
        cursor = self.connection.cursor()
        
        # Get dive information
        dive = cursor.execute("""
            SELECT d.*, s.site_name, s.site_code
            FROM dive_logs d
            JOIN sites s ON d.site_id = s.id
            WHERE d.id = ?
        """, (dive_id,)).fetchone()
        
        if not dive:
            return None
            
        # Get team members with signature status
        team = cursor.execute("""
            SELECT dt.*, w.full_name, w.worker_code, w.dive_certification,
                   ds.signature_hash, ds.signature_timestamp, ds.telegram_username
            FROM dive_team dt
            JOIN workers w ON dt.worker_id = w.id
            LEFT JOIN dive_signatures ds ON dt.dive_id = ds.dive_id AND dt.worker_id = ds.worker_id
            WHERE dt.dive_id = ?
            ORDER BY dt.role
        """, (dive_id,)).fetchall()
        
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
        
        elements.append(Paragraph("DIVE LOG SHEET - PALAZZO DESII - LAGOI", title_style))
        elements.append(Spacer(1, 10*mm))
        
        # Dive site info header
        header_data = [
            ['Dive Site:', dive['site_name'], '', 'Location:', 'Villa Imperiale, Posillipo'],
            ['Date:', dive['dive_date'], '', '', '']
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
        
        # Dive information
        info_data = [
            ['Dive Nr:', dive['dive_number'], 'Dive Time:', f"{dive['dive_start']} - {dive['dive_end']}"],
            ['Max Depth:', f"{dive['max_depth']}m", 'Avg Depth:', f"{dive['avg_depth']}m" if dive['avg_depth'] else ""],
            ['Water Temp:', f"{dive['water_temp']}°C" if dive['water_temp'] else "", 'Visibility:', f"{dive['visibility']}m" if dive['visibility'] else ""],
            ['Weather:', dive['weather_conditions'] or "", 'Current:', dive['current_strength'] or ""]
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
        team_header = ['Name', 'Bottom Time', 'Deco Time', 'BAR in', 'BAR out', 'BAR used', 'Signature']
        team_data = [team_header]
        
        for member in team:
            # Calculate BAR values (placeholder logic)
            bar_in = 200  # Standard starting pressure
            bar_used = member['air_consumed'] if member['air_consumed'] else 0
            bar_out = bar_in - bar_used if bar_used else ""
            
            # Signature field - show status or hash
            if member['signature_hash']:
                signature_text = f"✓ Signed\n{member['signature_timestamp'][:10]}\n{member['signature_hash'][:8]}..."
            else:
                signature_text = "Pending"
            
            team_data.append([
                member['full_name'],
                f"{member['bottom_time']} min" if member['bottom_time'] else "",
                f"{member['decompression_time']} min" if member['decompression_time'] else "",
                str(bar_in),
                str(bar_out) if bar_out else "",
                str(bar_used) if bar_used else "",
                signature_text
            ])
        
        # Add empty rows to match template
        for i in range(max(5 - len(team), 0)):
            team_data.append(["", "", "", "", "", "", ""])
        
        team_table = Table(team_data, colWidths=[35*mm, 20*mm, 20*mm, 18*mm, 18*mm, 18*mm, 35*mm])
        team_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (5, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('ROWHEIGHTS', (0, 1), (-1, -1), 15*mm),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        
        elements.append(Paragraph("Dive Team", styles['Heading2']))
        elements.append(Spacer(1, 5*mm))
        elements.append(team_table)
        
        # Objectives and notes section
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("Dive Objectives and Notes", styles['Heading2']))
        
        notes_data = [
            [dive['dive_objectives'] or "No objectives specified"],
            [dive['work_completed'] or "No work completed notes"]
        ]
        
        notes_table = Table(notes_data, colWidths=[165*mm])
        notes_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('ROWHEIGHTS', (0, 0), (-1, -1), 30*mm),
        ]))
        
        elements.append(notes_table)
        
        # Generate verification QR code
        if any(member['signature_hash'] for member in team):
            elements.append(Spacer(1, 10*mm))
            
            # Create QR code with dive and signature info
            qr_data = {
                'dive_id': dive_id,
                'dive_number': dive['dive_number'],
                'date': dive['dive_date'],
                'signatures': []
            }
            
            for member in team:
                if member['signature_hash']:
                    qr_data['signatures'].append({
                        'name': member['full_name'],
                        'hash': member['signature_hash'][:16],
                        'timestamp': member['signature_timestamp']
                    })
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            
            # Add QR code to document
            qr_style = ParagraphStyle(
                'QRStyle',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_RIGHT
            )
            
            elements.append(Paragraph("Digital Signature Verification", qr_style))
            elements.append(Image(bio, width=30*mm, height=30*mm, hAlign='RIGHT'))
        
        # Build PDF
        doc.build(elements)
        
        return output_path
    
    def generate_signature_report(self):
        """Generate a report of all signatures"""
        cursor = self.connection.cursor()
        
        signatures = cursor.execute("""
            SELECT ds.*, dl.dive_number, dl.dive_date, 
                   w.full_name, w.worker_code
            FROM dive_signatures ds
            JOIN dive_logs dl ON ds.dive_id = dl.id
            JOIN workers w ON ds.worker_id = w.id
            ORDER BY ds.signature_timestamp DESC
        """).fetchall()
        
        print("\n=== DIGITAL SIGNATURES REPORT ===")
        print(f"Total signatures: {len(signatures)}")
        
        for sig in signatures:
            print(f"\nDive: {sig['dive_number']} ({sig['dive_date']})")
            print(f"Signed by: {sig['full_name']} ({sig['worker_code']})")
            print(f"Timestamp: {sig['signature_timestamp']}")
            print(f"Hash: {sig['signature_hash'][:32]}...")
            print(f"Telegram: @{sig['telegram_username']}")
    
    def close(self):
        self.connection.close()


def main():
    """Generate signed dive log sheets"""
    db_path = "/Users/enzo/Desktop/Logoi2025/database/lagoi2025_simple.sqlite"
    
    # First run the telegram signature bot setup
    print("Setting up signature tables...")
    import telegram_signature_bot
    telegram_signature_bot.main()
    
    # Generate signed dive sheets
    generator = SignedDiveLogGenerator(db_path)
    
    output_dir = "/Users/enzo/Desktop/Logoi2025/database/signed_dive_logs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("\nGenerating signed dive log sheets...")
    
    for dive_id in [1, 2, 3]:
        output_path = os.path.join(output_dir, f"signed_divelog_{dive_id}.pdf")
        generator.generate_signed_dive_sheet(dive_id, output_path)
        print(f"✓ Generated: {output_path}")
    
    # Generate signature report
    generator.generate_signature_report()
    
    generator.close()
    
    print("\n✅ Dive log system ready!")
    print("\nNext steps:")
    print("1. Run the Telegram bot: python3 telegram_signature_bot.py")
    print("2. Team members sign via Telegram")
    print("3. Regenerate PDFs to include signatures")


if __name__ == "__main__":
    main()