#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install dependencies for Shipwreck Excavation QGIS Plugin
This script helps install all required Python packages
"""

import os
import sys
import subprocess
from pathlib import Path

def install_package(package):
    """Install a Python package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Main installation function"""
    print("=" * 60)
    print("Shipwreck Excavation Plugin - Dependency Installer")
    print("=" * 60)
    print()
    
    # Get the directory of this script
    script_dir = Path(__file__).parent
    requirements_file = script_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ Error: requirements.txt not found at {requirements_file}")
        return 1
    
    print(f"📋 Reading requirements from: {requirements_file}")
    print()
    
    # Core dependencies that must be installed
    core_packages = [
        "supabase>=2.0.0",
        "Pillow>=9.0.0",
        "reportlab>=3.6.0",
        "qrcode>=7.3.0",
        "python-dateutil>=2.8.0",
        "requests>=2.28.0"
    ]
    
    # Optional dependencies
    optional_packages = [
        "psycopg2-binary>=2.9.0",
        "opencv-python>=4.5.0",
        "vtk>=9.0.0",
        "pandas>=1.3.0",
        "openpyxl>=3.0.0",
        "python-telegram-bot>=20.0",
        "aiofiles>=23.0.0",
        "google-api-python-client>=2.0.0",
        "google-auth>=2.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=1.0.0",
        "numpy>=1.21.0"
    ]
    
    print("🔧 Installing CORE dependencies...")
    print("-" * 40)
    
    failed_core = []
    for package in core_packages:
        package_name = package.split(">=")[0]
        print(f"Installing {package_name}...", end=" ")
        if install_package(package):
            print("✅")
        else:
            print("❌")
            failed_core.append(package)
    
    print()
    print("🔧 Installing OPTIONAL dependencies...")
    print("-" * 40)
    
    failed_optional = []
    for package in optional_packages:
        package_name = package.split(">=")[0]
        print(f"Installing {package_name}...", end=" ")
        if install_package(package):
            print("✅")
        else:
            print("❌")
            failed_optional.append(package)
    
    print()
    print("=" * 60)
    print("📊 Installation Summary")
    print("=" * 60)
    
    if not failed_core:
        print("✅ All core dependencies installed successfully!")
    else:
        print("❌ Failed to install core dependencies:")
        for pkg in failed_core:
            print(f"   - {pkg}")
    
    if failed_optional:
        print("\n⚠️  Some optional dependencies failed to install:")
        for pkg in failed_optional:
            print(f"   - {pkg}")
        print("\nThese are optional and the plugin will work without them,")
        print("but some features may be limited.")
    
    print()
    print("📌 Next steps:")
    print("1. Restart QGIS")
    print("2. Enable the Shipwreck Excavation plugin")
    print("3. Configure database connection (Supabase)")
    print()
    
    return 0 if not failed_core else 1

if __name__ == "__main__":
    sys.exit(main())