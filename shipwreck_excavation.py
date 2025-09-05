# -*- coding: utf-8 -*-
"""
Shipwreck Excavation Management Plugin for QGIS
Main plugin class
"""

import os
import sys
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QIcon, QAction
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject, Qgis, QgsMessageLog

# Add plugin directory to Python path
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

# Now import our modules
try:
    from database.database_manager import DatabaseManager
    from ui.main_dialog import ShipwreckMainDialog
    from core.i18n_manager import I18nManager
    from sync.telegram_sync import TelegramSyncManager
    from utils.dependency_checker import DependencyChecker
    from sync.cloud_sync_manager import CloudSyncManager
    from ui.cloud_sync_dialog import CloudSyncDialog
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    IMPORTS_SUCCESSFUL = False
    IMPORT_ERROR = str(e)

class ShipwreckExcavation:
    """Main QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.
        
        :param iface: An interface instance that provides QGIS GUI access.
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        # Initialize locale
        self.i18n_manager = I18nManager(self.plugin_dir)
        self.translator = self.i18n_manager.get_translator()
        if self.translator:
            QCoreApplication.installTranslator(self.translator)
        
        # Initialize plugin variables
        self.actions = []
        self.menu = self.tr(u'&Shipwreck Excavation')
        self.toolbar = self.iface.addToolBar(u'ShipwreckExcavation')
        self.toolbar.setObjectName(u'ShipwreckExcavation')
        
        # Database manager
        self.db_manager = DatabaseManager()
        
        # Cloud sync manager
        self.cloud_sync_manager = CloudSyncManager()
        
        # Telegram sync manager
        self.telegram_sync = None
        
        # Main dialog
        self.main_dialog = None
        
        # Plugin settings
        self.settings = QSettings('ShipwreckExcavation', 'ShipwreckExcavation')
        
    def tr(self, message):
        """Get the translation for a string.
        
        :param message: String for translation.
        :type message: str
        
        :returns: Translated version of message.
        :rtype: str
        """
        return QCoreApplication.translate('ShipwreckExcavation', message)
    
    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar.
        
        :param icon_path: Path to the icon for this action
        :param text: Text for this action
        :param callback: Function to be called when the action is triggered
        :param enabled_flag: Enable/Disable the action
        :param add_to_menu: Add the action to the menu
        :param add_to_toolbar: Add the action to the toolbar
        :param status_tip: Optional text to show in status bar
        :param whats_this: Optional text to show in "What's This?"
        :param parent: Parent widget for the new action
        
        :returns: The action that was created
        :rtype: QAction
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        
        # Check if basic imports failed
        if not IMPORTS_SUCCESSFUL:
            # Try to install dependencies automatically without showing dialogs
            try:
                from utils.dependency_checker import DependencyChecker
                checker = DependencyChecker(self.iface.mainWindow())
                checker.check_dependencies()
                
                if checker.missing_required:
                    # Install silently in the background
                    QgsMessageLog.logMessage(
                        "Installing missing dependencies in background...", 
                        "Shipwreck Excavation", Qgis.Info
                    )
                    checker.install_missing_dependencies(show_progress=False)
                    
                    # Show message bar instead of dialog
                    self.iface.messageBar().pushMessage(
                        self.tr("Installing Dependencies"),
                        self.tr("Required packages are being installed. Please wait..."),
                        level=Qgis.Warning,
                        duration=5
                    )
                    
                    # Schedule a reload after installation
                    from qgis.PyQt.QtCore import QTimer
                    QTimer.singleShot(3000, self.reload_plugin)
                    return
                    
            except Exception as e:
                # Only show error if automatic installation fails
                from qgis.PyQt.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr("Dependency Error"),
                    self.tr(f"Could not install dependencies automatically.\n\n"
                           f"Error: {str(e)}\n\n"
                           f"Please install manually using:\n"
                           f"pip install supabase pillow reportlab qrcode python-dateutil requests")
                )
                return
        
        # Check dependencies on startup (will install silently if needed)
        try:
            DependencyChecker.check_and_install_on_startup(self.iface.mainWindow())
        except:
            # If dependency checker fails, continue anyway
            pass
        
        # Main action
        icon_path = os.path.join(self.plugin_dir, 'icons', 'shipwreck.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Shipwreck Excavation Management'),
            callback=self.run,
            parent=self.iface.mainWindow())
        
        # Create/Open Database action
        icon_path = os.path.join(self.plugin_dir, 'icons', 'database.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Create/Open Database'),
            callback=self.open_database,
            parent=self.iface.mainWindow())
        
        # Telegram Sync action
        icon_path = os.path.join(self.plugin_dir, 'icons', 'telegram.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Telegram Sync'),
            callback=self.toggle_telegram_sync,
            enabled_flag=False,
            parent=self.iface.mainWindow())
        
        # Cloud Sync action
        icon_path = os.path.join(self.plugin_dir, 'icons', 'cloud_sync.png')
        if not os.path.exists(icon_path):
            icon_path = os.path.join(self.plugin_dir, 'icons', 'telegram.png')  # Use telegram icon as fallback
        self.add_action(
            icon_path,
            text=self.tr(u'Cloud Sync'),
            callback=self.open_cloud_sync,
            enabled_flag=False,
            parent=self.iface.mainWindow())
        
        # Settings action
        icon_path = os.path.join(self.plugin_dir, 'icons', 'settings.png')
        self.add_action(
            icon_path,
            text=self.tr(u'Settings'),
            callback=self.open_settings,
            parent=self.iface.mainWindow())
        
        # Try to load saved database on startup
        saved_db_path = self.settings.value('shipwreck_excavation/db_path')
        if saved_db_path and os.path.exists(saved_db_path):
            if self.db_manager.connect(saved_db_path):
                self.iface.messageBar().pushMessage(
                    self.tr("Info"),
                    self.tr(f"Loaded saved database: {os.path.basename(saved_db_path)}"),
                    level=Qgis.Info,
                    duration=3
                )
                self.db_manager.add_layers_to_qgis()
                self.enable_features()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu(self.tr(u'&Shipwreck Excavation'), action)
            self.iface.removeToolBarIcon(action)
        
        # Remove the toolbar
        del self.toolbar
        
        # Close database connection
        if self.db_manager:
            self.db_manager.close()
        
        # Stop telegram sync
        if self.telegram_sync:
            self.telegram_sync.stop()

    def run(self):
        """Run method that performs all the real work"""
        # Check if database is connected
        if not self.db_manager.connection:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("No Database"),
                self.tr("Please create or open a database first.")
            )
            self.open_database()
            return
        
        # Create and show the dialog
        if not self.main_dialog:
            self.main_dialog = ShipwreckMainDialog(
                self.iface, 
                self.db_manager,
                self.settings,
                parent=self.iface.mainWindow()
            )
            # Set sync manager after creation
            if hasattr(self.main_dialog, 'set_sync_manager'):
                self.main_dialog.set_sync_manager(self.cloud_sync_manager)
        
        self.main_dialog.show()
        
    def open_database(self):
        """Open or create a database"""
        from .ui.database_dialog import DatabaseDialog
        
        dlg = DatabaseDialog(self.iface.mainWindow())
        if dlg.exec_():
            db_path = dlg.get_database_path()
            if dlg.is_new_database():
                # Create new database
                if self.db_manager.create_database(db_path):
                    # Save database path for next time
                    self.settings.setValue('shipwreck_excavation/db_path', db_path)
                    
                    self.iface.messageBar().pushMessage(
                        self.tr("Success"),
                        self.tr("Database created successfully"),
                        level=Qgis.Success
                    )
                    self.db_manager.add_layers_to_qgis()
                    self.enable_features()
                else:
                    QMessageBox.critical(
                        self.iface.mainWindow(),
                        self.tr("Error"),
                        self.tr("Failed to create database")
                    )
            else:
                # Open existing database
                if self.db_manager.connect(db_path):
                    # Save database path for next time
                    self.settings.setValue('shipwreck_excavation/db_path', db_path)
                    
                    self.iface.messageBar().pushMessage(
                        self.tr("Success"),
                        self.tr("Database opened successfully"),
                        level=Qgis.Success
                    )
                    self.db_manager.add_layers_to_qgis()
                    self.enable_features()
                else:
                    QMessageBox.critical(
                        self.iface.mainWindow(),
                        self.tr("Error"),
                        self.tr("Failed to open database")
                    )
    
    def reload_plugin(self):
        """Reload the plugin after installing dependencies"""
        try:
            from qgis import utils
            plugin_name = 'shipwreck_excavation'
            
            # Unload the plugin
            if plugin_name in utils.plugins:
                utils.unloadPlugin(plugin_name)
            
            # Remove from Python modules
            if plugin_name in sys.modules:
                del sys.modules[plugin_name]
            
            # Remove submodules
            modules_to_remove = []
            for mod in sys.modules:
                if mod.startswith(plugin_name + '.'):
                    modules_to_remove.append(mod)
            
            for mod in modules_to_remove:
                del sys.modules[mod]
            
            # Reload the plugin
            utils.loadPlugin(plugin_name)
            utils.startPlugin(plugin_name)
            
            self.iface.messageBar().pushMessage(
                self.tr("Success"),
                self.tr("Plugin reloaded with all dependencies"),
                level=Qgis.Success,
                duration=3
            )
        except Exception as e:
            QgsMessageLog.logMessage(f"Failed to reload plugin: {str(e)}", 
                                   "Shipwreck Excavation", Qgis.Critical)
    
    def enable_features(self):
        """Enable features after database connection"""
        # Enable telegram sync and cloud sync actions
        for action in self.actions:
            if action.text() in [self.tr(u'Telegram Sync'), self.tr(u'Cloud Sync')]:
                action.setEnabled(True)
        
        # Initialize telegram sync if token is available
        token = self.db_manager.get_setting('telegram_bot_token')
        if token:
            self.telegram_sync = TelegramSyncManager(self.db_manager, token)
        
        # Configure cloud sync with database path
        if self.cloud_sync_manager and self.db_manager.db_path:
            self.cloud_sync_manager.local_path = os.path.dirname(self.db_manager.db_path)
    
    def install_dependencies_and_restart(self):
        """Install missing dependencies using the installer script"""
        import subprocess
        from qgis.PyQt.QtWidgets import QProgressDialog, QMessageBox
        from qgis.PyQt.QtCore import Qt
        
        progress = QProgressDialog(
            self.tr("Installing dependencies..."), 
            self.tr("Cancel"), 
            0, 100, 
            self.iface.mainWindow()
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        progress.setValue(10)
        
        try:
            # Run the install script
            installer_path = os.path.join(self.plugin_dir, 'install_dependencies.py')
            result = subprocess.run(
                [sys.executable, installer_path],
                capture_output=True,
                text=True
            )
            
            progress.setValue(90)
            
            if result.returncode == 0:
                progress.setValue(100)
                QMessageBox.information(
                    self.iface.mainWindow(),
                    self.tr("Installation Complete"),
                    self.tr("Dependencies installed successfully!\n\nPlease restart QGIS for changes to take effect.")
                )
            else:
                QMessageBox.critical(
                    self.iface.mainWindow(),
                    self.tr("Installation Failed"),
                    self.tr(f"Failed to install dependencies:\n{result.stderr}")
                )
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr("Installation Error"),
                self.tr(f"Error installing dependencies: {str(e)}")
            )
        finally:
            progress.close()
    
    def toggle_telegram_sync(self):
        """Toggle telegram sync on/off"""
        if not self.telegram_sync:
            token = self.db_manager.get_setting('telegram_bot_token')
            if not token:
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    self.tr("No Token"),
                    self.tr("Please configure Telegram bot token in settings")
                )
                self.open_settings()
                return
            
            self.telegram_sync = TelegramSyncManager(self.db_manager, token)
        
        if self.telegram_sync.is_running():
            self.telegram_sync.stop()
            self.iface.messageBar().pushMessage(
                self.tr("Telegram Sync"),
                self.tr("Sync stopped"),
                level=Qgis.Info
            )
        else:
            self.telegram_sync.start()
            self.iface.messageBar().pushMessage(
                self.tr("Telegram Sync"),
                self.tr("Sync started"),
                level=Qgis.Success
            )
    
    def open_cloud_sync(self):
        """Open cloud sync configuration dialog"""
        if not self.db_manager.connection:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("No Database"),
                self.tr("Please open a database first")
            )
            return
        
        dlg = CloudSyncDialog(
            self.iface.mainWindow(),
            self.cloud_sync_manager,
            self.db_manager.db_path
        )
        
        # Connect signals
        dlg.sync_configured.connect(self.on_sync_configured)
        
        dlg.exec_()
    
    def on_sync_configured(self, provider, path):
        """Handle sync configuration"""
        self.iface.messageBar().pushMessage(
            self.tr("Cloud Sync"),
            self.tr(f"Configured sync with {provider}"),
            level=Qgis.Success,
            duration=3
        )
    
    def open_settings(self):
        """Open settings dialog"""
        from .ui.settings_dialog import SettingsDialog
        
        dlg = SettingsDialog(self.db_manager, self.settings, self.iface.mainWindow())
        if dlg.exec_():
            # Reload settings
            self.i18n_manager.set_language(self.settings.value('language', 'en'))
            
            # Restart telegram sync if token changed
            if self.telegram_sync:
                self.telegram_sync.stop()
                token = self.db_manager.get_setting('telegram_bot_token')
                if token:
                    self.telegram_sync = TelegramSyncManager(self.db_manager, token)
                    self.telegram_sync.start()