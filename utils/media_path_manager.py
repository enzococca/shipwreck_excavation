# -*- coding: utf-8 -*-
"""
Media Path Manager for Shipwreck Excavation Plugin
Handles relative paths and media organization
"""

import os
import shutil
from pathlib import Path
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import QObject, pyqtSignal

class MediaPathManager(QObject):
    """Manages media file paths and organization"""
    
    # Signals
    media_copied = pyqtSignal(str, str)  # old_path, new_path
    progress_updated = pyqtSignal(int, int)  # current, total
    
    def __init__(self, db_path, db_manager=None):
        super().__init__()
        self.db_path = Path(db_path) if db_path else None
        self.db_manager = db_manager
        self.media_root = None
        
        # Try to get configured media path from settings
        QgsMessageLog.logMessage(f"MediaPathManager init - db_manager: {self.db_manager}", "Shipwreck Excavation", Qgis.Info)
        if self.db_manager:
            configured_path = self.db_manager.get_setting('media_base_path')
            QgsMessageLog.logMessage(f"MediaPathManager - configured_path from settings: {configured_path}", "Shipwreck Excavation", Qgis.Info)
            if configured_path and os.path.exists(configured_path):
                # Check if the path already includes 'media' folder
                if configured_path.endswith('/media') or configured_path.endswith('\\media'):
                    self.media_root = Path(configured_path)
                else:
                    self.media_root = Path(configured_path) / "media"
                QgsMessageLog.logMessage(f"Using configured media path: {self.media_root}", 
                                       "Shipwreck Excavation", Qgis.Info)
            else:
                QgsMessageLog.logMessage(f"Configured path not found or doesn't exist: {configured_path}", "Shipwreck Excavation", Qgis.Warning)
        else:
            QgsMessageLog.logMessage(f"No db_manager provided to MediaPathManager", "Shipwreck Excavation", Qgis.Warning)
        
        # Fallback to db_path if no configured path
        if not self.media_root and self.db_path and self.db_path.exists():
            self.media_root = self.db_path.parent / "media"
            QgsMessageLog.logMessage(f"Using fallback media path: {self.media_root}", 
                                   "Shipwreck Excavation", Qgis.Warning)
            
        if self.media_root:
            self._ensure_media_structure()
    
    def _ensure_media_structure(self):
        """Ensure media directory structure exists"""
        if not self.media_root:
            return
            
        subdirs = ['photos', 'videos', '3d_models', 'documents', 'thumbnails']
        for subdir in subdirs:
            (self.media_root / subdir).mkdir(parents=True, exist_ok=True)
        
        QgsMessageLog.logMessage(f"Media structure created at: {self.media_root}", 
                               "Shipwreck Excavation", Qgis.Info)
    
    def get_media_type_folder(self, media_type):
        """Get folder name for media type"""
        type_folders = {
            'photo': 'photos',
            'video': 'videos',
            '3d': '3d_models',
            'document': 'documents'
        }
        return type_folders.get(media_type, 'photos')
    
    def import_media_file(self, source_path, media_type='photo', copy=True):
        """Import a media file to the managed structure
        
        Args:
            source_path: Path to source file
            media_type: Type of media (photo, video, 3d, document)
            copy: If True, copy file; if False, move file
        
        Returns:
            Relative path to imported file or None if failed
        """
        if not self.media_root or not os.path.exists(source_path):
            return None
        
        source_path = Path(source_path)
        folder = self.get_media_type_folder(media_type)
        dest_dir = self.media_root / folder
        
        # Generate unique filename if exists
        dest_path = dest_dir / source_path.name
        counter = 1
        while dest_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        try:
            if copy:
                shutil.copy2(source_path, dest_path)
            else:
                shutil.move(str(source_path), str(dest_path))
            
            # Return relative path from media root parent
            # This ensures consistent relative paths regardless of base path
            if self.media_root.parent:
                rel_path = dest_path.relative_to(self.media_root.parent)
            else:
                # Fallback to just the path within media folder
                rel_path = Path("media") / dest_path.relative_to(self.media_root)
            
            self.media_copied.emit(str(source_path), str(dest_path))
            QgsMessageLog.logMessage(f"Media imported: {rel_path}", 
                                   "Shipwreck Excavation", Qgis.Info)
            
            return str(rel_path)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Failed to import media: {e}", 
                                   "Shipwreck Excavation", Qgis.Critical)
            return None
    
    def get_absolute_path(self, relative_path):
        """Convert relative path to absolute path"""
        if not relative_path:
            return None
            
        # If already absolute, return as is
        if os.path.isabs(relative_path):
            return relative_path
            
        # Use configured media root if available
        if self.media_root:
            # Get the base path (parent of media folder)
            base_path = self.media_root.parent
            abs_path = base_path / relative_path
            return str(abs_path) if abs_path.exists() else None
        elif self.db_path:
            # Fallback to db_path
            abs_path = self.db_path.parent / relative_path
            return str(abs_path) if abs_path.exists() else None
        
        return None
    
    def get_relative_path(self, absolute_path):
        """Convert absolute path to relative path"""
        if not absolute_path or not self.db_path:
            return None
            
        try:
            abs_path = Path(absolute_path)
            if abs_path.is_relative_to(self.db_path.parent):
                return str(abs_path.relative_to(self.db_path.parent))
            else:
                # File is outside project directory
                return str(absolute_path)
        except:
            return str(absolute_path)
    
    def migrate_existing_media(self, db_manager, progress_callback=None):
        """Migrate existing media files to relative paths
        
        Args:
            db_manager: Database manager instance
            progress_callback: Optional callback for progress updates
        """
        # Get all media records
        media_query = "SELECT id, file_path, media_type FROM media WHERE file_path IS NOT NULL"
        media_records = db_manager.execute_query(media_query)
        
        if not media_records:
            return
        
        total = len(media_records)
        migrated = 0
        failed = 0
        
        for i, record in enumerate(media_records):
            if progress_callback:
                progress_callback(i + 1, total)
            
            media_id = record[0]
            old_path = record[1]
            media_type = record[2]
            
            # Skip if already relative
            if not os.path.isabs(old_path):
                continue
            
            # Skip if file doesn't exist
            if not os.path.exists(old_path):
                QgsMessageLog.logMessage(f"Media file not found: {old_path}", 
                                       "Shipwreck Excavation", Qgis.Warning)
                failed += 1
                continue
            
            # Import to managed structure
            new_rel_path = self.import_media_file(old_path, media_type, copy=True)
            
            if new_rel_path:
                # Update database
                update_query = "UPDATE media SET file_path = ? WHERE id = ?"
                db_manager.execute_query(update_query, (new_rel_path, media_id))
                migrated += 1
            else:
                failed += 1
        
        QgsMessageLog.logMessage(
            f"Media migration complete: {migrated} migrated, {failed} failed", 
            "Shipwreck Excavation", Qgis.Info
        )
    
    def create_thumbnail(self, media_path, media_type='photo'):
        """Create thumbnail for media file"""
        if not media_path or not self.media_root:
            return None
        
        abs_path = self.get_absolute_path(media_path)
        if not abs_path or not os.path.exists(abs_path):
            return None
        
        thumb_dir = self.media_root / 'thumbnails'
        source_path = Path(abs_path)
        thumb_name = f"thumb_{source_path.stem}.jpg"
        thumb_path = thumb_dir / thumb_name
        
        if thumb_path.exists():
            return str(thumb_path.relative_to(self.db_path.parent))
        
        try:
            if media_type == 'photo':
                from PIL import Image
                img = Image.open(abs_path)
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                img.save(thumb_path, "JPEG", quality=85)
                
            elif media_type == 'video':
                import cv2
                cap = cv2.VideoCapture(abs_path)
                ret, frame = cap.read()
                if ret:
                    # Resize frame
                    height, width = frame.shape[:2]
                    scale = min(200/width, 200/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                    cv2.imwrite(str(thumb_path), frame)
                cap.release()
                
            elif media_type == '3d':
                # For 3D models, create a placeholder or render preview
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', (200, 200), color='lightgray')
                draw = ImageDraw.Draw(img)
                draw.text((70, 90), "3D Model", fill='black')
                img.save(thumb_path, "JPEG")
            
            if thumb_path.exists():
                return str(thumb_path.relative_to(self.db_path.parent))
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Failed to create thumbnail: {e}", 
                                   "Shipwreck Excavation", Qgis.Warning)
        
        return None
    
    def cleanup_orphaned_media(self, db_manager):
        """Remove media files that are no longer referenced in database"""
        if not self.media_root:
            return
        
        # Get all referenced media paths
        query = "SELECT file_path FROM media WHERE file_path IS NOT NULL"
        db_paths = {record[0] for record in db_manager.execute_query(query)}
        
        # Convert to absolute paths
        db_abs_paths = set()
        for path in db_paths:
            abs_path = self.get_absolute_path(path)
            if abs_path:
                db_abs_paths.add(Path(abs_path))
        
        # Check all files in media directory
        orphaned = []
        for media_file in self.media_root.rglob('*'):
            if media_file.is_file() and media_file not in db_abs_paths:
                orphaned.append(media_file)
        
        # Move orphaned files to trash folder
        if orphaned:
            trash_dir = self.media_root / '_trash'
            trash_dir.mkdir(exist_ok=True)
            
            for file_path in orphaned:
                try:
                    dest = trash_dir / file_path.name
                    shutil.move(str(file_path), str(dest))
                except Exception as e:
                    QgsMessageLog.logMessage(f"Failed to move orphaned file: {e}", 
                                           "Shipwreck Excavation", Qgis.Warning)
        
        QgsMessageLog.logMessage(f"Cleanup complete: {len(orphaned)} orphaned files moved to trash", 
                               "Shipwreck Excavation", Qgis.Info)