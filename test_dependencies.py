#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify dependency checking and installation
"""

import sys
import os

# Add plugin directory to path
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

def test_imports():
    """Test if all required imports work"""
    print("Testing required imports...")
    
    required = [
        ('supabase', 'Supabase client'),
        ('PIL', 'Image processing (Pillow)'),
        ('reportlab', 'PDF generation'),
        ('qrcode', 'QR code generation'),
        ('dateutil', 'Date utilities'),
        ('requests', 'HTTP requests')
    ]
    
    optional = [
        ('cv2', 'OpenCV for video processing'),
        ('pandas', 'Excel export'),
        ('telegram', 'Telegram bot'),
        ('psycopg2', 'PostgreSQL driver')
    ]
    
    print("\n=== REQUIRED PACKAGES ===")
    missing_required = []
    for module, desc in required:
        try:
            __import__(module)
            print(f"✓ {module}: {desc}")
        except ImportError:
            print(f"✗ {module}: {desc}")
            missing_required.append(module)
    
    print("\n=== OPTIONAL PACKAGES ===")
    missing_optional = []
    for module, desc in optional:
        try:
            __import__(module)
            print(f"✓ {module}: {desc}")
        except ImportError:
            print(f"✗ {module}: {desc}")
            missing_optional.append(module)
    
    print("\n=== SUMMARY ===")
    if not missing_required:
        print("✅ All required packages are installed!")
    else:
        print(f"❌ Missing required packages: {', '.join(missing_required)}")
    
    if missing_optional:
        print(f"⚠️  Missing optional packages: {', '.join(missing_optional)}")
    
    return len(missing_required) == 0

def test_dependency_checker():
    """Test the dependency checker itself"""
    print("\n=== TESTING DEPENDENCY CHECKER ===")
    
    try:
        from utils.dependency_checker import DependencyChecker
        print("✓ DependencyChecker imported successfully")
        
        checker = DependencyChecker()
        has_deps = checker.check_dependencies()
        
        if checker.missing_required:
            print(f"\nMissing required dependencies detected:")
            for pkg in checker.missing_required:
                print(f"  - {pkg}")
        
        if has_deps:
            print("\n✅ Dependency checker reports all required packages installed")
        else:
            print("\n❌ Dependency checker found missing required packages")
            
    except Exception as e:
        print(f"✗ Error testing dependency checker: {e}")

if __name__ == "__main__":
    print("Shipwreck Excavation Plugin - Dependency Test")
    print("=" * 50)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test dependency checker
    test_dependency_checker()
    
    print("\n" + "=" * 50)
    if imports_ok:
        print("✅ Plugin is ready to use!")
    else:
        print("❌ Please install missing dependencies using:")
        print("   python install_dependencies.py")