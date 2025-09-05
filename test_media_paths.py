#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Media Path Configuration
Verifies that media paths are correctly read from QSettings
"""

import os
import sys
from PyQt5.QtCore import QSettings

def test_media_paths():
    """Test reading media paths from QSettings"""
    print("=" * 60)
    print("Testing Media Path Configuration")
    print("=" * 60)
    print()
    
    # Create settings object with same organization/application as plugin
    settings = QSettings('ShipwreckExcavation', 'ShipwreckExcavation')
    
    print(f"Settings file location: {settings.fileName()}")
    print(f"Organization: {settings.organizationName()}")
    print(f"Application: {settings.applicationName()}")
    print()
    
    # List all keys in settings
    print("All keys in settings:")
    all_keys = settings.allKeys()
    if all_keys:
        for key in sorted(all_keys):
            value = settings.value(key)
            print(f"  {key}: {value}")
    else:
        print("  (no keys found)")
    print()
    
    # Check for media path specifically
    print("Checking media path keys:")
    media_keys = [
        'media_base_path',
        'media_storage_path',
        'shipwreck_excavation/media_base_path',
        'shipwreck_excavation/media_storage_path'
    ]
    
    found_path = None
    for key in media_keys:
        value = settings.value(key)
        if value:
            print(f"  ✓ {key}: {value}")
            if os.path.exists(str(value)):
                print(f"    → Path exists!")
                found_path = value
            else:
                print(f"    → Path does NOT exist")
        else:
            print(f"  ✗ {key}: (not set)")
    
    print()
    if found_path:
        print(f"✓ Media path is configured: {found_path}")
        
        # Check for media subdirectories
        print("\nChecking media subdirectories:")
        subdirs = ['media', 'media/photos', 'media/videos', 'media/3d_models', 'media/documents']
        for subdir in subdirs:
            full_path = os.path.join(found_path, subdir)
            if os.path.exists(full_path):
                print(f"  ✓ {subdir} exists")
            else:
                print(f"  ✗ {subdir} does not exist")
    else:
        print("✗ No media path configured!")
        print("\nTo configure:")
        print("1. Open QGIS")
        print("2. Open the Shipwreck Excavation plugin")
        print("3. Go to Settings → Database Settings")
        print("4. Set the Media Storage Path")
    
    print()
    print("=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    test_media_paths()