# -*- coding: utf-8 -*-
"""
Telegram sync manager for QGIS plugin
Handles synchronization of data from Telegram bot
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal, QThread
from qgis.core import QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

class SyncWorker(QThread):
    """Worker thread for synchronization"""
    
    sync_progress = pyqtSignal(str)
    sync_error = pyqtSignal(str)
    sync_completed = pyqtSignal(int)  # Number of items synced
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_path = db_manager.db_path  # Store path instead of manager
        self.is_running = True
        
    def run(self):
        """Run sync process"""
        import sqlite3
        
        # Create new connection in this thread
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Enable spatialite if available
            try:
                conn.enable_load_extension(True)
                conn.load_extension("mod_spatialite")
            except:
                pass
            
            # Get pending messages from queue
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM telegram_sync_queue 
                WHERE processed = 0 
                ORDER BY created_at ASC 
                LIMIT 50
            """)
            messages = cursor.fetchall()
            
            if not messages:
                self.sync_completed.emit(0)
                return
            
            synced_count = 0
            
            for msg in messages:
                if not self.is_running:
                    break
                
                try:
                    msg_data = json.loads(msg['message_data'])
                    
                    if msg['message_type'] == 'find':
                        self.sync_progress.emit(f"Syncing find {msg_data.get('find_number', 'Unknown')}")
                        
                        # Process coordinates if available
                        geometry = None
                        if 'latitude' in msg_data and 'longitude' in msg_data:
                            # Convert from WGS84 to UTM Zone 48N
                            point = QgsPointXY(msg_data['longitude'], msg_data['latitude'])
                            
                            # Transform coordinates
                            crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
                            crs_utm = QgsCoordinateReferenceSystem("EPSG:32648")
                            transform = QgsCoordinateTransform(crs_wgs84, crs_utm, QgsProject.instance())
                            
                            point_utm = transform.transform(point)
                            geometry = QgsGeometry.fromPointXY(point_utm)
                        
                        # Prepare find data
                        find_data = {
                            'site_id': msg_data['site_id'],
                            'find_number': msg_data['find_number'],
                            'material_type': msg_data.get('material_type'),
                            'object_type': msg_data.get('object_type'),
                            'description': msg_data.get('description'),
                            'condition': msg_data.get('condition'),
                            'depth': msg_data.get('depth'),
                            'find_date': msg_data.get('find_date', datetime.now().strftime('%Y-%m-%d')),
                            'finder_name': msg_data.get('telegram_user'),
                            'telegram_sync': True
                        }
                        
                        # Add find to database
                        find_id = self.db_manager.add_find(find_data, geometry)
                        
                        if find_id:
                            # Process photos
                            for photo in msg_data.get('photos', []):
                                media_data = {
                                    'media_type': 'photo',
                                    'file_name': photo['file_name'],
                                    'file_path': photo['file_path'],
                                    'description': photo.get('caption', ''),
                                    'photographer': msg_data.get('telegram_user'),
                                    'capture_date': datetime.now()
                                }
                                
                                self.db_manager.add_media(media_data, 'find', find_id)
                            
                            # Mark as processed
                            self.db_manager.mark_telegram_processed(msg['id'])
                            synced_count += 1
                        else:
                            self.db_manager.mark_telegram_processed(msg['id'], 
                                error="Failed to add find to database")
                    
                    elif msg['message_type'] == 'dive_log':
                        self.sync_progress.emit(f"Syncing dive log {msg_data.get('dive_number', 'Unknown')}")
                        
                        # Prepare dive log data
                        dive_data = {
                            'site_id': msg_data['site_id'],
                            'dive_number': msg_data['dive_number'],
                            'dive_date': msg_data['dive_date'],
                            'dive_start': msg_data['dive_start'],
                            'dive_end': msg_data['dive_end'],
                            'max_depth': msg_data['max_depth'],
                            'dive_objectives': msg_data['dive_purpose'],  # Map dive_purpose to dive_objectives
                            'work_completed': msg_data.get('work_completed'),
                            'telegram_sync': True
                        }
                        
                        # Insert dive log
                        cursor.execute("""
                            INSERT INTO dive_logs (
                                site_id, dive_number, dive_date, dive_start, dive_end,
                                max_depth, dive_objectives, work_completed, telegram_sync
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            dive_data['site_id'],
                            dive_data['dive_number'],
                            dive_data['dive_date'],
                            dive_data['dive_start'],
                            dive_data['dive_end'],
                            dive_data['max_depth'],
                            dive_data['dive_objectives'],
                            dive_data['work_completed'],
                            1
                        ))
                        
                        dive_id = cursor.lastrowid
                        
                        # Add team members
                        for member in msg_data.get('team_members', []):
                            cursor.execute("""
                                INSERT INTO dive_team_members (dive_id, member_name)
                                VALUES (?, ?)
                            """, (dive_id, member))
                        
                        # Mark as processed
                        cursor.execute("""
                            UPDATE telegram_sync_queue 
                            SET processed = 1, processed_at = datetime('now')
                            WHERE id = ?
                        """, (msg['id'],))
                        
                        conn.commit()
                        synced_count += 1
                        
                    elif msg['message_type'] == 'photo':
                        # Handle standalone photos
                        pass
                    
                    elif msg['message_type'] == 'location':
                        # Handle location updates
                        pass
                        
                except Exception as e:
                    error_msg = f"Error processing message {msg['id']}: {str(e)}"
                    self.sync_error.emit(error_msg)
                    # Mark with error in our thread connection
                    cursor.execute("""
                        UPDATE telegram_sync_queue 
                        SET processed = 1, processed_at = datetime('now'), 
                            error_message = ?
                        WHERE id = ?
                    """, (error_msg, msg['id']))
                    conn.commit()
            
            # Update last sync time
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ('last_telegram_sync', datetime('now'), datetime('now'))
            """)
            conn.commit()
            
            self.sync_completed.emit(synced_count)
            
        except Exception as e:
            self.sync_error.emit(f"Sync error: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def stop(self):
        """Stop the worker"""
        self.is_running = False

class TelegramSyncManager(QObject):
    """Manages synchronization with Telegram bot"""
    
    sync_started = pyqtSignal()
    sync_finished = pyqtSignal(int)  # Number of items synced
    sync_status = pyqtSignal(str)
    
    def __init__(self, db_manager, bot_token):
        super().__init__()
        self.db_manager = db_manager
        self.bot_token = bot_token
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_data)
        self.sync_worker = None
        self._is_running = False
        
        # Get sync interval from settings (default 5 minutes)
        sync_interval = int(self.db_manager.get_setting('sync_interval') or 300)
        self.sync_timer.setInterval(sync_interval * 1000)  # Convert to milliseconds
    
    def start(self):
        """Start automatic synchronization"""
        if not self._is_running:
            self._is_running = True
            self.sync_timer.start()
            self.sync_data()  # Initial sync
            self.sync_status.emit("Telegram sync started")
    
    def stop(self):
        """Stop automatic synchronization"""
        self._is_running = False
        self.sync_timer.stop()
        
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait()
        
        self.sync_status.emit("Telegram sync stopped")
    
    def is_running(self):
        """Check if sync is running"""
        return self._is_running
    
    def sync_data(self):
        """Perform synchronization"""
        if self.sync_worker and self.sync_worker.isRunning():
            # Previous sync still running
            return
        
        self.sync_started.emit()
        self.sync_status.emit("Syncing with Telegram...")
        
        # Create and start worker
        self.sync_worker = SyncWorker(self.db_manager)
        self.sync_worker.sync_progress.connect(self.on_sync_progress)
        self.sync_worker.sync_error.connect(self.on_sync_error)
        self.sync_worker.sync_completed.connect(self.on_sync_completed)
        self.sync_worker.start()
    
    def on_sync_progress(self, message):
        """Handle sync progress"""
        self.sync_status.emit(message)
    
    def on_sync_error(self, error):
        """Handle sync error"""
        self.sync_status.emit(f"Error: {error}")
    
    def on_sync_completed(self, count):
        """Handle sync completion"""
        self.sync_finished.emit(count)
        
        if count > 0:
            self.sync_status.emit(f"Synced {count} items from Telegram")
        else:
            self.sync_status.emit("No new items to sync")
        
        # Update last sync time in settings
        self.db_manager.set_setting('last_telegram_sync', datetime.now().isoformat())