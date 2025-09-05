#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe dependency installer for Shipwreck Excavation QGIS Plugin
This script installs dependencies without opening new QGIS instances
"""

import sys
import subprocess
import os
from pathlib import Path

def get_qgis_python():
    """Get the correct Python interpreter for QGIS"""
    # If running from within QGIS
    if 'QGIS' in sys.executable:
        # Try to find the actual Python, not QGIS executable
        import platform
        python_version = platform.python_version_tuple()
        
        # Try different possible Python locations
        possible_pythons = [
            f"/usr/bin/python{python_version[0]}.{python_version[1]}",
            "/usr/bin/python3",
            "/usr/local/bin/python3",
            sys.executable.replace('/QGIS.app/', '/Python.framework/')
        ]
        
        for python_path in possible_pythons:
            if os.path.exists(python_path):
                return python_path
    
    return sys.executable

def install_with_pip_module():
    """Install using pip module directly"""
    try:
        import pip
        # Try to use pip's internal API
        try:
            from pip._internal import main as pipmain
        except ImportError:
            from pip import main as pipmain
        
        return pipmain
    except ImportError:
        return None

def install_package(package, use_user=True):
    """Install a single package"""
    pipmain = install_with_pip_module()
    
    if pipmain:
        # Use pip module directly
        args = ['install', '--quiet']
        if use_user:
            args.append('--user')
        args.append(package)
        
        try:
            result = pipmain(args)
            return result == 0
        except:
            return False
    else:
        # Fallback to subprocess
        python = get_qgis_python()
        cmd = [python, '-m', 'pip', 'install', '--quiet']
        if use_user:
            cmd.append('--user')
        cmd.append(package)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

def main():
    """Main installation function"""
    print("=" * 60)
    print("Shipwreck Excavation - Safe Dependency Installer")
    print("=" * 60)
    print()
    
    # Core dependencies
    packages = [
        ('supabase', 'supabase>=2.0.0', True),
        ('Pillow', 'Pillow>=9.0.0', True),
        ('reportlab', 'reportlab>=3.6.0', True),
        ('qrcode', 'qrcode>=7.3.0', True),
        ('python-dateutil', 'python-dateutil>=2.8.0', True),
        ('requests', 'requests>=2.28.0', True),
        ('psycopg2', 'psycopg2-binary>=2.9.0', False),
        ('opencv-python', 'opencv-python>=4.5.0', False),
        ('pandas', 'pandas>=1.3.0', False),
        ('openpyxl', 'openpyxl>=3.0.0', False),
        ('python-telegram-bot', 'python-telegram-bot>=20.0', False),
    ]
    
    print("Installing dependencies (this won't open new QGIS instances)...")
    print()
    
    failed_required = []
    failed_optional = []
    
    for name, package, required in packages:
        status = "REQUIRED" if required else "optional"
        print(f"Installing {name} ({status})...", end=" ")
        
        if install_package(package):
            print("")
        else:
            print("")
            if required:
                failed_required.append(package)
            else:
                failed_optional.append(package)
    
    print()
    print("=" * 60)
    
    if not failed_required:
        print(" All required dependencies installed successfully!")
        print()
        print("The plugin is ready to use. Please restart QGIS if it's running.")
    else:
        print(" Some required dependencies failed to install:")
        for pkg in failed_required:
            print(f"  - {pkg}")
        print()
        print("Try installing them manually with:")
        print(f"  pip install --user {' '.join(failed_required)}")
    
    if failed_optional:
        print()
        print("  Some optional dependencies failed (plugin will work without them):")
        for pkg in failed_optional:
            print(f"  - {pkg}")
    
    print()
    return 0 if not failed_required else 1

if __name__ == "__main__":
    sys.exit(main())