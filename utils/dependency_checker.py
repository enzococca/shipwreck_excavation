# -*- coding: utf-8 -*-
"""
Dependency Checker for Shipwreck Excavation Plugin
Checks and installs required Python packages
"""

import os
import sys
import subprocess
import importlib
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import QMessageBox, QProgressDialog
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal

class PackageInstaller(QThread):
    """Thread for installing packages without blocking QGIS"""
    progress_update = pyqtSignal(str)
    package_installed = pyqtSignal(str)
    package_failed = pyqtSignal(str)
    finished_all = pyqtSignal()
    
    def __init__(self, packages_to_install):
        super().__init__()
        self.packages_to_install = packages_to_install
        
    def run(self):
        """Run the installation in a separate thread"""
        for package_name in self.packages_to_install:
            self.progress_update.emit(f"Installing {package_name}...")
            if self.install_package_internal(package_name):
                self.package_installed.emit(package_name)
            else:
                self.package_failed.emit(package_name)
        self.finished_all.emit()
    
    def install_package_internal(self, package_name):
        """Install a package using pip without opening new QGIS instances"""
        try:
            # Use the pip module directly instead of subprocess
            import pip
            # Try to use pip's internal API
            try:
                from pip._internal import main as pipmain
            except ImportError:
                from pip import main as pipmain
            
            # Install quietly
            result = pipmain(['install', '--quiet', package_name])
            return result == 0
        except:
            # Fallback to subprocess but with proper Python interpreter
            try:
                python_path = sys.executable
                # On macOS, if QGIS is running, we need to use the Python inside QGIS
                if sys.platform == 'darwin' and 'QGIS' in python_path:
                    # Find the actual Python executable, not QGIS
                    import platform
                    python_version = platform.python_version_tuple()
                    python_path = f"/usr/bin/python{python_version[0]}.{python_version[1]}"
                    if not os.path.exists(python_path):
                        python_path = "/usr/bin/python3"
                
                # Use PIPE to capture output instead of showing it
                result = subprocess.run(
                    [python_path, '-m', 'pip', 'install', '--quiet', '--user', package_name],
                    capture_output=True,
                    text=True,
                    check=False
                )
                return result.returncode == 0
            except Exception as e:
                QgsMessageLog.logMessage(f"Failed to install {package_name}: {str(e)}", 
                                       "Shipwreck Excavation", Qgis.Critical)
                return False

class DependencyChecker:
    """Check and install plugin dependencies"""
    
    # Required packages with import names and pip names
    REQUIRED_PACKAGES = {
        # Core dependencies - MUST be installed
        'supabase': {'pip_name': 'supabase>=2.0.0', 'required': True, 'description': 'Database connectivity'},
        'PIL': {'pip_name': 'Pillow>=9.0.0', 'required': True, 'description': 'Image processing'},
        'reportlab': {'pip_name': 'reportlab>=3.6.0', 'required': True, 'description': 'PDF generation'},
        'qrcode': {'pip_name': 'qrcode>=7.3.0', 'required': True, 'description': 'QR code generation'},
        'dateutil': {'pip_name': 'python-dateutil>=2.8.0', 'required': True, 'description': 'Date utilities'},
        'requests': {'pip_name': 'requests>=2.28.0', 'required': True, 'description': 'HTTP requests'},
        
        # Optional dependencies
        'cv2': {'pip_name': 'opencv-python>=4.5.0', 'required': False, 'description': 'Video processing and analysis'},
        'vtk': {'pip_name': 'vtk>=9.0.0', 'required': False, 'description': '3D visualization and rendering'},
        'pandas': {'pip_name': 'pandas>=1.3.0', 'required': False, 'description': 'Excel export'},
        'openpyxl': {'pip_name': 'openpyxl>=3.0.0', 'required': False, 'description': 'Excel files'},
        'telegram': {'pip_name': 'python-telegram-bot>=20.0', 'required': False, 'description': 'Telegram bot'},
        'numpy': {'pip_name': 'numpy>=1.21.0', 'required': False, 'description': 'Numeric operations'},
        'psycopg2': {'pip_name': 'psycopg2-binary>=2.9.0', 'required': False, 'description': 'PostgreSQL'},
        'aiofiles': {'pip_name': 'aiofiles>=23.0.0', 'required': False, 'description': 'Async file I/O'}
    }
    
    def __init__(self, parent=None):
        self.parent = parent
        self.missing_packages = []
        self.missing_required = []
        self.installer_thread = None
        
    def check_dependencies(self):
        """Check if all dependencies are installed"""
        QgsMessageLog.logMessage("Checking plugin dependencies...", "Shipwreck Excavation", Qgis.Info)
        
        for import_name, info in self.REQUIRED_PACKAGES.items():
            try:
                importlib.import_module(import_name)
                QgsMessageLog.logMessage(f"✓ {import_name} is installed", "Shipwreck Excavation", Qgis.Info)
            except ImportError:
                self.missing_packages.append((import_name, info['pip_name']))
                if info['required']:
                    self.missing_required.append(info['pip_name'])
                QgsMessageLog.logMessage(f"✗ {import_name} is NOT installed", "Shipwreck Excavation", Qgis.Warning)
        
        return len(self.missing_required) == 0
    
    def install_package(self, package_name):
        """Install a single package using pip (deprecated - use install_missing_dependencies instead)"""
        try:
            import pip
            # Try to use pip's internal API
            try:
                from pip._internal import main as pipmain
            except ImportError:
                from pip import main as pipmain
            
            # Install quietly
            result = pipmain(['install', '--quiet', '--user', package_name])
            return result == 0
        except Exception as e:
            QgsMessageLog.logMessage(f"Failed to install {package_name}: {str(e)}", 
                                   "Shipwreck Excavation", Qgis.Critical)
            return False
    
    def install_missing_dependencies(self, show_progress=True):
        """Install all missing dependencies using a background thread"""
        if not self.missing_packages:
            return True
        
        # Extract just the pip names
        packages_to_install = [pip_name for _, pip_name in self.missing_packages]
        
        if show_progress and self.parent:
            self.progress = QProgressDialog("Checking dependencies...", None, 
                                          0, len(packages_to_install), self.parent)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)  # Can't cancel
            self.progress.setMinimumDuration(0)
            self.progress.show()
            
            self.installed = []
            self.failed = []
            
            # Create and start the installer thread
            self.installer_thread = PackageInstaller(packages_to_install)
            self.installer_thread.progress_update.connect(self.on_progress_update)
            self.installer_thread.package_installed.connect(self.on_package_installed)
            self.installer_thread.package_failed.connect(self.on_package_failed)
            self.installer_thread.finished_all.connect(self.on_installation_finished)
            self.installer_thread.start()
            
            # Wait for thread to finish (with event processing)
            while self.installer_thread.isRunning():
                QgsMessageLog.logMessage("Waiting for installation to complete...", 
                                       "Shipwreck Excavation", Qgis.Info)
                self.installer_thread.wait(100)
                if self.parent:
                    from qgis.PyQt.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
                    
        else:
            # No progress dialog, install directly
            installed = []
            failed = []
            for _, pip_name in self.missing_packages:
                installer = PackageInstaller([pip_name])
                if installer.install_package_internal(pip_name):
                    installed.append(pip_name)
                else:
                    failed.append(pip_name)
            
            return len(failed) == 0
        
        return True
    
    def on_progress_update(self, message):
        """Update progress dialog"""
        if hasattr(self, 'progress'):
            self.progress.setLabelText(message)
            
    def on_package_installed(self, package_name):
        """Handle successful package installation"""
        self.installed.append(package_name)
        QgsMessageLog.logMessage(f"✓ Installed {package_name}", 
                               "Shipwreck Excavation", Qgis.Success)
        if hasattr(self, 'progress'):
            self.progress.setValue(len(self.installed) + len(self.failed))
            
    def on_package_failed(self, package_name):
        """Handle failed package installation"""
        self.failed.append(package_name)
        QgsMessageLog.logMessage(f"✗ Failed to install {package_name}", 
                               "Shipwreck Excavation", Qgis.Warning)
        if hasattr(self, 'progress'):
            self.progress.setValue(len(self.installed) + len(self.failed))
            
    def on_installation_finished(self):
        """Handle completion of all installations"""
        if hasattr(self, 'progress'):
            self.progress.close()
            
        # Show results only if there were issues
        if self.parent and self.failed:
            # Only show required packages that failed
            failed_required = [pkg for pkg in self.failed if pkg in self.missing_required]
            if failed_required:
                QMessageBox.warning(
                    self.parent,
                    "Missing Required Dependencies",
                    f"The following required dependencies could not be installed:\n"
                    f"{', '.join(failed_required)}\n\n"
                    f"Please install them manually using:\n"
                    f"pip install --user {' '.join(failed_required)}\n\n"
                    f"The plugin may not work correctly without these packages."
                )
        elif self.parent and self.installed and len(self.installed) == len(self.missing_packages):
            # All packages installed successfully
            from qgis.core import Qgis
            if hasattr(self.parent, 'iface'):
                self.parent.iface.messageBar().pushMessage(
                    "Dependencies Installed",
                    f"Successfully installed {len(self.installed)} packages",
                    level=Qgis.Success,
                    duration=3
                )
    
    def show_dependency_dialog(self):
        """Show dialog with dependency status"""
        if not self.parent:
            return
        
        if not self.missing_packages:
            QMessageBox.information(
                self.parent,
                "Dependencies OK",
                "All required dependencies are installed!"
            )
            return
        
        # Build detailed message with descriptions
        msg = "<h3>Missing Dependencies</h3>"
        msg += "<p>The following modules need to be installed for the plugin to work properly:</p>"
        
        if self.missing_required:
            msg += "<h4>🔴 Required Modules:</h4><ul>"
            for import_name, pip_name in self.missing_packages:
                if pip_name in self.missing_required:
                    desc = self.REQUIRED_PACKAGES[import_name]['description']
                    msg += f"<li><b>{pip_name}</b> - {desc}</li>"
            msg += "</ul>"
        
        optional_missing = [(imp, pip) for imp, pip in self.missing_packages 
                          if pip not in self.missing_required]
        if optional_missing:
            msg += "<h4>🟡 Optional Modules:</h4><ul>"
            for import_name, pip_name in optional_missing:
                desc = self.REQUIRED_PACKAGES[import_name]['description']
                msg += f"<li><b>{pip_name}</b> - {desc}</li>"
            msg += "</ul>"
        
        msg += "<br><p><b>Click OK to install them automatically.</b></p>"
        
        msgBox = QMessageBox(self.parent)
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle("Missing Dependencies")
        msgBox.setText(msg)
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        if msgBox.exec() == QMessageBox.Ok:
            self.install_missing_dependencies()
    
    @staticmethod
    def check_and_install_on_startup(parent=None):
        """Check dependencies on plugin startup - silent automatic installation"""
        checker = DependencyChecker(parent)
        checker.check_dependencies()
        
        # If there are missing required packages, try to install them silently
        if checker.missing_required:
            QgsMessageLog.logMessage(
                f"Auto-installing required packages: {', '.join(checker.missing_required)}", 
                "Shipwreck Excavation", Qgis.Info
            )
            
            # Try silent installation first
            success = checker.install_missing_dependencies(show_progress=False)
            
            # Re-check after installation
            checker_verify = DependencyChecker(parent)
            checker_verify.check_dependencies()
            
            # Only show dialog if still missing required packages
            if checker_verify.missing_required and parent:
                checker_verify.show_dependency_dialog()
        elif checker.missing_packages:
            # Only optional packages missing, install silently in background
            QgsMessageLog.logMessage(
                f"Optional packages not installed: {', '.join([p[1] for p in checker.missing_packages])}", 
                "Shipwreck Excavation", Qgis.Info
            )
            # Don't install optional packages automatically
        
        return checker