#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create placeholder icons for the plugin
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(text, filename, color=(0, 100, 200)):
    """Create a simple icon with text"""
    # Create image
    size = (64, 64)
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw circle background
    margin = 4
    draw.ellipse([margin, margin, size[0]-margin, size[1]-margin], 
                 fill=color, outline=(0, 0, 0))
    
    # Draw text
    try:
        # Try to use a better font if available
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font = ImageFont.load_default()
    
    # Get text bounds
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center text
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    
    # Save
    img.save(filename, 'PNG')
    print(f"Created {filename}")

# Create icons
icons = {
    'shipwreck.png': ('⚓', (0, 100, 200)),
    'database.png': ('DB', (100, 150, 50)),
    'telegram.png': ('TG', (0, 136, 204)),
    'settings.png': ('⚙', (128, 128, 128)),
}

for filename, (text, color) in icons.items():
    create_icon(text, filename, color)

print("Icons created successfully!")