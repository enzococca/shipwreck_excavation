# -*- coding: utf-8 -*-
"""
Cloud Sync Manager for Shipwreck Excavation Plugin
Handles automatic synchronization with cloud storage services
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal, QTimer, QSettings
from qgis.core import QgsMessageLog, Qgis

class SyncWorker(QThread):
    """Worker thread for sync operations"""
    
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(bool, str)  # success, message
    conflict_detected = pyqtSignal(dict)  # conflict info
    
    def __init__(self, local_path, remote_path, sync_type='full'):
        super().__init__()
        self.local_path = Path(local_path)
        self.remote_path = Path(remote_path)
        self.sync_type = sync_type
        self.cancelled = False
    
    def run(self):
        """Run sync operation"""
        try:
            if self.sync_type == 'full':
                self.full_sync()
            elif self.sync_type == 'upload':
                self.upload_changes()
            elif self.sync_type == 'download':
                self.download_changes()
            
            if not self.cancelled:
                self.finished.emit(True, "Sincronizzazione completata")
        except Exception as e:
            self.finished.emit(False, f"Errore sincronizzazione: {str(e)}")
    
    def full_sync(self):
        """Perform full bidirectional sync"""
        # Get file lists
        local_files = self.get_file_list(self.local_path)
        remote_files = self.get_file_list(self.remote_path)
        
        total_files = len(set(local_files.keys()) | set(remote_files.keys()))
        processed = 0
        
        # Check each file
        all_files = set(local_files.keys()) | set(remote_files.keys())
        
        for rel_path in all_files:
            if self.cancelled:
                break
                
            local_info = local_files.get(rel_path)
            remote_info = remote_files.get(rel_path)
            
            if local_info and not remote_info:
                # File only exists locally - upload
                self.copy_file(
                    self.local_path / rel_path,
                    self.remote_path / rel_path
                )
            elif remote_info and not local_info:
                # File only exists remotely - download
                self.copy_file(
                    self.remote_path / rel_path,
                    self.local_path / rel_path
                )
            elif local_info and remote_info:
                # File exists in both - check for conflicts
                if local_info['mtime'] > remote_info['mtime']:
                    # Local is newer - upload
                    self.copy_file(
                        self.local_path / rel_path,
                        self.remote_path / rel_path
                    )
                elif remote_info['mtime'] > local_info['mtime']:
                    # Remote is newer - download
                    self.copy_file(
                        self.remote_path / rel_path,
                        self.local_path / rel_path
                    )
                elif local_info['hash'] != remote_info['hash']:
                    # Same modification time but different content - conflict!
                    self.handle_conflict(rel_path, local_info, remote_info)
            
            processed += 1
            percentage = int((processed / total_files) * 100)
            self.progress.emit(f"Sincronizzazione {processed}/{total_files}", percentage)
    
    def get_file_list(self, base_path):
        """Get list of files with metadata"""
        files = {}
        
        if not base_path.exists():
            return files
        
        for file_path in base_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                rel_path = file_path.relative_to(base_path)
                files[str(rel_path)] = {
                    'mtime': file_path.stat().st_mtime,
                    'size': file_path.stat().st_size,
                    'hash': self.get_file_hash(file_path)
                }
        
        return files
    
    def get_file_hash(self, file_path):
        """Calculate file hash for comparison"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None
    
    def copy_file(self, source, dest):
        """Copy file preserving metadata"""
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    
    def handle_conflict(self, rel_path, local_info, remote_info):
        """Handle sync conflict"""
        conflict_info = {
            'file': rel_path,
            'local_time': datetime.fromtimestamp(local_info['mtime']),
            'remote_time': datetime.fromtimestamp(remote_info['mtime']),
            'local_size': local_info['size'],
            'remote_size': remote_info['size']
        }
        self.conflict_detected.emit(conflict_info)
    
    def stop(self):
        """Stop sync operation"""
        self.cancelled = True


class CloudSyncManager(QObject):
    """Manages cloud synchronization"""
    
    # Signals
    sync_started = pyqtSignal()
    sync_finished = pyqtSignal(bool, str)
    sync_progress = pyqtSignal(str, int)
    conflict_detected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self.sync_worker = None
        self.auto_sync_timer = QTimer()
        self.auto_sync_timer.timeout.connect(self.auto_sync)
        self.conflict_resolution = 'ask'  # ask, local, remote, newest
        
        # Load settings
        self.load_settings()
    
    def load_settings(self):
        """Load sync settings"""
        self.settings.beginGroup('ShipwreckExcavation/CloudSync')
        
        self.sync_enabled = self.settings.value('enabled', False, type=bool)
        self.sync_provider = self.settings.value('provider', 'dropbox')
        self.sync_path = self.settings.value('path', '')
        self.auto_sync_enabled = self.settings.value('auto_sync', True, type=bool)
        self.sync_interval = self.settings.value('interval', 300, type=int)  # 5 minutes
        self.conflict_resolution = self.settings.value('conflict_resolution', 'ask')
        
        self.settings.endGroup()
        
        # Start auto sync if enabled
        if self.sync_enabled and self.auto_sync_enabled:
            self.start_auto_sync()
    
    def save_settings(self):
        """Save sync settings"""
        self.settings.beginGroup('ShipwreckExcavation/CloudSync')
        
        self.settings.setValue('enabled', self.sync_enabled)
        self.settings.setValue('provider', self.sync_provider)
        self.settings.setValue('path', self.sync_path)
        self.settings.setValue('auto_sync', self.auto_sync_enabled)
        self.settings.setValue('interval', self.sync_interval)
        self.settings.setValue('conflict_resolution', self.conflict_resolution)
        
        self.settings.endGroup()
    
    def configure_sync(self, provider, cloud_path, local_path):
        """Configure sync settings"""
        self.sync_provider = provider
        self.sync_path = cloud_path
        self.local_path = local_path
        self.sync_enabled = True
        
        # Create sync metadata file
        self.create_sync_metadata()
        
        # Save settings
        self.save_settings()
        
        # Start auto sync if enabled
        if self.auto_sync_enabled:
            self.start_auto_sync()
        
        QgsMessageLog.logMessage(
            f"Sincronizzazione configurata: {provider} - {cloud_path}", 
            "Shipwreck Excavation", Qgis.Info
        )
    
    def create_sync_metadata(self):
        """Create sync metadata file"""
        metadata = {
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'provider': self.sync_provider,
            'sync_id': hashlib.md5(
                f"{self.sync_provider}:{self.sync_path}".encode()
            ).hexdigest()
        }
        
        metadata_path = Path(self.local_path) / '.sync_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def start_sync(self, sync_type='full'):
        """Start sync operation"""
        if self.sync_worker and self.sync_worker.isRunning():
            QgsMessageLog.logMessage(
                "Sincronizzazione già in corso", 
                "Shipwreck Excavation", Qgis.Warning
            )
            return
        
        if not self.sync_enabled or not self.sync_path:
            QgsMessageLog.logMessage(
                "Sincronizzazione non configurata", 
                "Shipwreck Excavation", Qgis.Warning
            )
            return
        
        # Create worker
        self.sync_worker = SyncWorker(
            self.local_path,
            self.sync_path,
            sync_type
        )
        
        # Connect signals
        self.sync_worker.progress.connect(self.on_sync_progress)
        self.sync_worker.finished.connect(self.on_sync_finished)
        self.sync_worker.conflict_detected.connect(self.on_conflict_detected)
        
        # Start sync
        self.sync_started.emit()
        self.sync_worker.start()
        
        QgsMessageLog.logMessage(
            f"Sincronizzazione {sync_type} avviata", 
            "Shipwreck Excavation", Qgis.Info
        )
    
    def stop_sync(self):
        """Stop current sync operation"""
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait()
    
    def start_auto_sync(self):
        """Start automatic sync timer"""
        if self.sync_enabled and self.auto_sync_enabled:
            self.auto_sync_timer.start(self.sync_interval * 1000)
            QgsMessageLog.logMessage(
                f"Sincronizzazione automatica attivata (ogni {self.sync_interval} secondi)", 
                "Shipwreck Excavation", Qgis.Info
            )
    
    def stop_auto_sync(self):
        """Stop automatic sync timer"""
        self.auto_sync_timer.stop()
    
    def auto_sync(self):
        """Perform automatic sync"""
        if not self.sync_worker or not self.sync_worker.isRunning():
            self.start_sync('full')
    
    def on_sync_progress(self, message, percentage):
        """Handle sync progress"""
        self.sync_progress.emit(message, percentage)
    
    def on_sync_finished(self, success, message):
        """Handle sync completion"""
        self.sync_finished.emit(success, message)
        
        # Update last sync time
        if success:
            self.settings.setValue(
                'ShipwreckExcavation/CloudSync/last_sync',
                datetime.now().isoformat()
            )
    
    def on_conflict_detected(self, conflict_info):
        """Handle sync conflict"""
        if self.conflict_resolution == 'ask':
            # Emit signal for UI to handle
            self.conflict_detected.emit(conflict_info)
        elif self.conflict_resolution == 'local':
            # Keep local version
            self.resolve_conflict(conflict_info['file'], 'local')
        elif self.conflict_resolution == 'remote':
            # Keep remote version
            self.resolve_conflict(conflict_info['file'], 'remote')
        elif self.conflict_resolution == 'newest':
            # Keep newest version
            if conflict_info['local_time'] > conflict_info['remote_time']:
                self.resolve_conflict(conflict_info['file'], 'local')
            else:
                self.resolve_conflict(conflict_info['file'], 'remote')
    
    def resolve_conflict(self, file_path, resolution):
        """Resolve a sync conflict"""
        local_file = Path(self.local_path) / file_path
        remote_file = Path(self.sync_path) / file_path
        
        if resolution == 'local':
            # Copy local to remote
            shutil.copy2(local_file, remote_file)
        elif resolution == 'remote':
            # Copy remote to local
            shutil.copy2(remote_file, local_file)
        elif resolution == 'both':
            # Keep both with different names
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            conflict_name = f"{local_file.stem}_conflict_{timestamp}{local_file.suffix}"
            conflict_path = local_file.parent / conflict_name
            shutil.copy2(local_file, conflict_path)
            shutil.copy2(remote_file, local_file)
    
    def get_sync_status(self):
        """Get current sync status"""
        status = {
            'enabled': self.sync_enabled,
            'provider': self.sync_provider,
            'path': self.sync_path,
            'auto_sync': self.auto_sync_enabled,
            'syncing': self.sync_worker.isRunning() if self.sync_worker else False
        }
        
        # Get last sync time
        last_sync = self.settings.value('ShipwreckExcavation/CloudSync/last_sync')
        if last_sync:
            status['last_sync'] = datetime.fromisoformat(last_sync)
        
        return status
    
    def clone_from_cloud(self, cloud_path, local_path, progress_callback=None):
        """Clone entire project from cloud to local
        
        Args:
            cloud_path: Path to cloud folder containing database and media
            local_path: Local path where to clone
            progress_callback: Optional callback(message, percentage)
        
        Returns:
            Tuple (success, db_path, error_message)
        """
        try:
            # Check if cloud path exists
            cloud_path = Path(cloud_path)
            if not cloud_path.exists():
                return False, None, f"Cloud path not found: {cloud_path}"
            
            # Find database file
            db_files = list(cloud_path.glob('*.sqlite')) + list(cloud_path.glob('*.db'))
            if not db_files:
                return False, None, "No database file found in cloud folder"
            
            db_file = db_files[0]  # Use first database found
            
            # Create local directory
            local_path = Path(local_path)
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Count total files for progress
            total_files = sum(1 for _ in cloud_path.rglob('*') if _.is_file())
            copied_files = 0
            
            # Copy all files maintaining structure
            for source_file in cloud_path.rglob('*'):
                if source_file.is_file():
                    # Calculate relative path
                    rel_path = source_file.relative_to(cloud_path)
                    dest_file = local_path / rel_path
                    
                    # Create destination directory
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(source_file, dest_file)
                    
                    copied_files += 1
                    if progress_callback:
                        percentage = int((copied_files / total_files) * 100)
                        progress_callback(f"Copying {rel_path.name}", percentage)
            
            # Return path to cloned database
            local_db_path = local_path / db_file.name
            
            # Save clone info
            self.save_clone_info(cloud_path, local_path, local_db_path)
            
            return True, str(local_db_path), None
            
        except Exception as e:
            return False, None, str(e)
    
    def save_clone_info(self, cloud_path, local_path, db_path):
        """Save information about cloned project"""
        clone_info = {
            'cloud_path': str(cloud_path),
            'local_path': str(local_path),
            'db_path': str(db_path),
            'cloned_at': datetime.now().isoformat()
        }
        
        # Save to settings
        self.settings.beginGroup('ShipwreckExcavation/ClonedProjects')
        project_id = hashlib.md5(str(cloud_path).encode()).hexdigest()[:8]
        self.settings.setValue(project_id, clone_info)
        self.settings.endGroup()