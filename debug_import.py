#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug import issues"""

import sys
import os

print("Current directory:", os.getcwd())
print("Script directory:", os.path.dirname(__file__))

# Test direct import
try:
    with open('__init__.py', 'r') as f:
        content = f.read()
    print("\n__init__.py content:")
    print("-" * 40)
    print(content)
    print("-" * 40)
    
    # Check if classFactory is defined
    if 'def classFactory' in content:
        print("✓ classFactory function is defined in __init__.py")
    else:
        print("✗ classFactory function NOT found in __init__.py")
        
except Exception as e:
    print(f"Error reading __init__.py: {e}")

# Test module import
print("\nTesting module import...")
try:
    # Add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    import shipwreck_excavation
    print(f"✓ Module imported: {shipwreck_excavation}")
    print(f"  Module file: {shipwreck_excavation.__file__}")
    print(f"  Module attributes: {[attr for attr in dir(shipwreck_excavation) if not attr.startswith('_')]}")
    
    if hasattr(shipwreck_excavation, 'classFactory'):
        print("✓ classFactory found in module")
    else:
        print("✗ classFactory NOT found in module")
        
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()