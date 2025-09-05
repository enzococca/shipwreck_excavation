# -*- coding: utf-8 -*-
"""
Database management module for Shipwreck Excavation
Handles SpatiaLite database operations
"""

import os
import sqlite3
from datetime import datetime
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import QObject, pyqtSignal
import json

class DatabaseManager(QObject):
    """Manages SpatiaLite database connections and operations"""
    
    db_created = pyqtSignal(str)
    db_error = pyqtSignal(str)
    
    def __init__(self, db_path=None):
        super().__init__()
        self.connection = None
        self.db_path = db_path
        self.crs = QgsCoordinateReferenceSystem("EPSG:32648")  # UTM Zone 48N for Bintan
        self.spatialite_available = False
    
    def is_connected(self):
        """Check if database is connected"""
        return self.connection is not None
        
    def create_database(self, db_path):
        """Create a new SpatiaLite database with schema"""
        try:
            # Load mod_spatialite
            self.connection = sqlite3.connect(db_path)
            self.connection.enable_load_extension(True)
            
            # Try to load SpatiaLite extension
            spatialite_loaded = False
            try:
                self.connection.load_extension("mod_spatialite")
                spatialite_loaded = True
            except:
                # Try alternative paths
                for ext in ["mod_spatialite.so", "mod_spatialite.dylib", "mod_spatialite.dll"]:
                    try:
                        self.connection.load_extension(ext)
                        spatialite_loaded = True
                        break
                    except:
                        continue
            
            if not spatialite_loaded:
                # Continue without SpatiaLite - will use simple SQLite
                print("Warning: SpatiaLite extension not loaded, using standard SQLite")
            
            self.spatialite_available = spatialite_loaded
            self.db_path = db_path
            self.connection.row_factory = sqlite3.Row
            
            # Choose schema based on SpatiaLite availability
            if spatialite_loaded:
                schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            else:
                schema_path = os.path.join(os.path.dirname(__file__), 'schema_sqlite.sql')
                
            print(f"Using schema: {schema_path}")
            
            with open(schema_path, 'r') as f:
                schema = f.read()
            
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in schema.split(';') if s.strip()]
            cursor = self.connection.cursor()
            
            for statement in statements:
                try:
                    if statement.upper().startswith('SELECT INITSPATIALMETADATA'):
                        if spatialite_loaded:
                            cursor.execute(statement)
                    elif 'ADDGEOMETRYCOLUMN' in statement.upper():
                        if spatialite_loaded:
                            cursor.execute(statement)
                    else:
                        cursor.execute(statement)
                except Exception as e:
                    print(f"Warning executing: {statement[:50]}... - {e}")
                    # Continue with other statements
            
            self.connection.commit()
            
            # Set row factory after creation
            self.connection.row_factory = sqlite3.Row
            
            self.db_created.emit(db_path)
            return True
            
        except Exception as e:
            self.db_error.emit(f"Database creation error: {str(e)}")
            if self.connection:
                self.connection.close()
                self.connection = None
            return False
    
    def connect(self, db_path):
        """Connect to existing database"""
        try:
            self.connection = sqlite3.connect(db_path)
            self.connection.enable_load_extension(True)
            
            try:
                self.connection.load_extension("mod_spatialite")
            except:
                pass
                
            self.db_path = db_path
            self.connection.row_factory = sqlite3.Row
            return True
            
        except Exception as e:
            self.db_error.emit(str(e))
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        if not self.connection:
            return None
            
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            self.db_error.emit(str(e))
            return None
    
    def execute_update(self, query, params=None):
        """Execute an update/insert query"""
        if not self.connection:
            self.db_error.emit("No database connection")
            print("DEBUG: No database connection in execute_update")
            return False
            
        try:
            cursor = self.connection.cursor()
            print(f"DEBUG: Executing query: {query}")
            print(f"DEBUG: With params: {params}")
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            lastrowid = cursor.lastrowid
            print(f"DEBUG: Query executed successfully, lastrowid: {lastrowid}")
            return lastrowid if lastrowid else True
        except Exception as e:
            error_msg = f"Database error: {str(e)}\nQuery: {query}\nParams: {params}"
            self.db_error.emit(error_msg)
            print(f"DEBUG: {error_msg}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def add_layers_to_qgis(self, layers=None):
        """Add database layers to QGIS project"""
        if not self.db_path:
            return
            
        if layers is None:
            layers = ['sites', 'excavation_areas', 'finds']
        
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        group = root.addGroup("Shipwreck Excavation")
        
        for layer_name in layers:
            uri = QgsDataSourceUri()
            uri.setDatabase(self.db_path)
            uri.setDataSource('', layer_name, 'geom')
            
            layer = QgsVectorLayer(uri.uri(), layer_name, 'spatialite')
            
            if layer.isValid():
                project.addMapLayer(layer, False)
                group.addLayer(layer)
            else:
                self.db_error.emit(f"Failed to load layer: {layer_name}")
    
    def get_setting(self, key):
        """Get a setting value"""
        result = self.execute_query("SELECT value FROM settings WHERE key = ?", (key,))
        if result:
            # Handle both dict and tuple results
            if isinstance(result[0], dict):
                return result[0]['value']
            else:
                return result[0][0]  # For tuple results
        return None
    
    def set_setting(self, key, value):
        """Set a setting value"""
        return self.execute_update(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, datetime.now())
        )
    
    def add_find(self, data, geometry=None):
        """Add a new find record"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        
        if geometry:
            columns += ', geom'
            if self.spatialite_available:
                placeholders += ', GeomFromText(?, 32648)'
            else:
                placeholders += ', ?'
            values = list(data.values()) + [geometry.asWkt()]
        else:
            values = list(data.values())
        
        query = f"INSERT INTO finds ({columns}) VALUES ({placeholders})"
        return self.execute_update(query, values)
    
    def get_finds(self, site_id=None, area_id=None, limit=None):
        """Get finds with optional filters"""
        if self.spatialite_available:
            query = """
                SELECT f.*, AsText(f.geom) as geom_wkt,
                       COUNT(DISTINCT mr.media_id) as media_count
                FROM finds f
                LEFT JOIN media_relations mr ON mr.related_type = 'find' AND mr.related_id = f.id
                WHERE 1=1
            """
        else:
            query = """
                SELECT f.*, f.geom as geom_wkt,
                       COUNT(DISTINCT mr.media_id) as media_count
                FROM finds f
                LEFT JOIN media_relations mr ON mr.related_type = 'find' AND mr.related_id = f.id
                WHERE 1=1
            """
        params = []
        
        if site_id:
            query += " AND f.site_id = ?"
            params.append(site_id)
            
        if area_id:
            query += " AND f.area_id = ?"
            params.append(area_id)
            
        query += " GROUP BY f.id ORDER BY f.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
            
        results = self.execute_query(query, params)
        
        # Convert tuples to dicts if necessary
        if results and not isinstance(results[0], dict):
            # Get column names from cursor description
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            
            # Convert each row to dict
            dict_results = []
            for row in results:
                dict_results.append(dict(zip(columns, row)))
            return dict_results
            
        return results
    
    def add_media(self, media_data, related_type, related_id):
        """Add media file and create relation"""
        # Insert media record
        media_id = self.execute_update(
            """INSERT INTO media (media_type, file_name, file_path, file_size, 
                                 mime_type, description, photographer, capture_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (media_data['media_type'], media_data['file_name'], media_data['file_path'],
             media_data.get('file_size'), media_data.get('mime_type'),
             media_data.get('description'), media_data.get('photographer'),
             media_data.get('capture_date'))
        )
        
        if media_id:
            # Create relation
            self.execute_update(
                """INSERT INTO media_relations (media_id, related_type, related_id, relation_type)
                   VALUES (?, ?, ?, ?)""",
                (media_id, related_type, related_id, media_data.get('relation_type', 'documentation'))
            )
            
        return media_id
    
    def get_telegram_queue(self, limit=10):
        """Get unprocessed telegram messages"""
        return self.execute_query(
            """SELECT * FROM telegram_sync_queue 
               WHERE processed = 0 
               ORDER BY created_at ASC 
               LIMIT ?""",
            (limit,)
        )
    
    def mark_telegram_processed(self, queue_id, error=None):
        """Mark telegram message as processed"""
        if error:
            return self.execute_update(
                """UPDATE telegram_sync_queue 
                   SET processed = 1, processed_at = ?, error_message = ?
                   WHERE id = ?""",
                (datetime.now(), error, queue_id)
            )
        else:
            return self.execute_update(
                """UPDATE telegram_sync_queue 
                   SET processed = 1, processed_at = ?
                   WHERE id = ?""",
                (datetime.now(), queue_id)
            )