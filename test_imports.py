#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test all imports for the plugin
Run this from the plugin directory to test if all modules import correctly
"""

import sys
import os

# Add plugin directory to path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, plugin_dir)

print(f"Testing imports from: {plugin_dir}")
print("-" * 50)

# Test main imports
try:
    print("Testing main module imports...")
    from database.db_manager import DatabaseManager
    print("✓ DatabaseManager imported successfully")
    
    from ui.main_dialog import ShipwreckMainDialog
    print("✓ ShipwreckMainDialog imported successfully")
    
    from core.i18n_manager import I18nManager
    print("✓ I18nManager imported successfully")
    
    from sync.telegram_sync import TelegramSyncManager
    print("✓ TelegramSyncManager imported successfully")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test UI widgets
try:
    print("\nTesting UI widget imports...")
    
    # Change to ui directory
    ui_dir = os.path.join(plugin_dir, 'ui')
    sys.path.insert(0, ui_dir)
    
    from finds_widget import FindsWidget
    print("✓ FindsWidget imported successfully")
    
    from media_widget import MediaWidget
    print("✓ MediaWidget imported successfully")
    
    from divelog_widget import DiveLogWidget
    print("✓ DiveLogWidget imported successfully")
    
    from workers_widget import WorkersWidget
    print("✓ WorkersWidget imported successfully")
    
    from costs_widget import CostsWidget
    print("✓ CostsWidget imported successfully")
    
    from site_widget import SiteWidget
    print("✓ SiteWidget imported successfully")
    
except ImportError as e:
    print(f"✗ Widget import error: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
print("\nNow try loading the plugin in QGIS.")