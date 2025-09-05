"""
PostgreSQL Database Manager for Supabase
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from PyQt5.QtCore import QSettings
import os
from typing import Dict, Any, List, Optional

class PostgreSQLDatabaseManager:
    """Database manager for PostgreSQL/Supabase"""
    
    def __init__(self, connection_string: str = None):
        self.settings = QSettings('Lagoi', 'ShipwreckExcavation')
        
        # Use provided connection string or load from settings/env
        if connection_string:
            self.connection_string = connection_string
        else:
            # Try environment variable first
            self.connection_string = os.environ.get('SUPABASE_DB_URL', 
                'postgresql://postgres.bqlmbmkffhzayinboanu:lagoi2025lagoi@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require')
        
        self.connection = None
        self.media_path_manager = None
    
    def set_media_path_manager(self, media_path_manager):
        """Set media path manager"""
        self.media_path_manager = media_path_manager
    
    def connect(self):
        """Establish database connection"""
        if not self.connection or self.connection.closed:
            self.connection = psycopg2.connect(self.connection_string)
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query and return results"""
        self.connect()
        with self.connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """Execute INSERT query and return ID"""
        self.connect()
        with self.connection.cursor() as cur:
            # Add RETURNING id if not present
            if 'returning' not in query.lower():
                query += ' RETURNING id'
            cur.execute(query, params)
            result = cur.fetchone()
            self.connection.commit()
            return result[0] if result else None
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute UPDATE/DELETE query"""
        self.connect()
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            rows_affected = cur.rowcount
            self.connection.commit()
            return rows_affected
    
    # Site methods
    def get_sites(self) -> List[Dict]:
        """Get all sites with PostGIS geometry"""
        query = """
            SELECT id, site_code, site_name, site_type,
                   ST_X(location::geometry) as longitude,
                   ST_Y(location::geometry) as latitude,
                   description, discovery_date, period, status,
                   created_at, updated_at
            FROM sites
            ORDER BY site_name
        """
        return self.execute_query(query)
    
    def get_site_by_id(self, site_id: int) -> Optional[Dict]:
        """Get site by ID"""
        query = """
            SELECT id, site_code, site_name, site_type,
                   ST_X(location::geometry) as longitude,
                   ST_Y(location::geometry) as latitude,
                   description, discovery_date, period, status,
                   created_at, updated_at
            FROM sites
            WHERE id = %s
        """
        results = self.execute_query(query, (site_id,))
        return results[0] if results else None
    
    def add_site(self, site_data: Dict) -> int:
        """Add new site"""
        # Create PostGIS point if coordinates provided
        location = None
        if site_data.get('latitude') and site_data.get('longitude'):
            location = f"POINT({site_data['longitude']} {site_data['latitude']})"
        
        query = """
            INSERT INTO sites (site_code, site_name, site_type, location,
                             description, discovery_date, period, status)
            VALUES (%s, %s, %s, ST_GeogFromText(%s), %s, %s, %s, %s)
        """
        
        params = (
            site_data['site_code'],
            site_data['site_name'],
            site_data.get('site_type'),
            location,
            site_data.get('description'),
            site_data.get('discovery_date'),
            site_data.get('period'),
            site_data.get('status', 'active')
        )
        
        return self.execute_insert(query, params)
    
    def update_site(self, site_id: int, site_data: Dict) -> bool:
        """Update site"""
        # Build dynamic update query
        fields = []
        params = []
        
        for key, value in site_data.items():
            if key not in ['id', 'created_at', 'updated_at', 'latitude', 'longitude']:
                fields.append(f"{key} = %s")
                params.append(value)
        
        # Handle location update
        if 'latitude' in site_data and 'longitude' in site_data:
            location = f"POINT({site_data['longitude']} {site_data['latitude']})"
            fields.append("location = ST_GeogFromText(%s)")
            params.append(location)
        
        params.append(site_id)
        
        query = f"""
            UPDATE sites 
            SET {', '.join(fields)}
            WHERE id = %s
        """
        
        return self.execute_update(query, tuple(params)) > 0
    
    def delete_site(self, site_id: int) -> bool:
        """Delete site"""
        query = "DELETE FROM sites WHERE id = %s"
        return self.execute_update(query, (site_id,)) > 0
    
    # Find methods
    def get_finds_by_site(self, site_id: int) -> List[Dict]:
        """Get finds for a specific site"""
        query = """
            SELECT f.*, 
                   ST_X(f.location::geometry) as longitude,
                   ST_Y(f.location::geometry) as latitude
            FROM finds f
            WHERE f.site_id = %s
            ORDER BY f.find_date DESC, f.find_number
        """
        return self.execute_query(query, (site_id,))
    
    def get_find_by_id(self, find_id: int) -> Optional[Dict]:
        """Get find by ID"""
        query = """
            SELECT f.*, 
                   ST_X(f.location::geometry) as longitude,
                   ST_Y(f.location::geometry) as latitude,
                   s.site_code, s.site_name
            FROM finds f
            JOIN sites s ON f.site_id = s.id
            WHERE f.id = %s
        """
        results = self.execute_query(query, (find_id,))
        return results[0] if results else None
    
    def add_find(self, find_data: Dict) -> int:
        """Add new find"""
        # Create PostGIS point if coordinates provided
        location = None
        if find_data.get('latitude') and find_data.get('longitude'):
            location = f"POINT({find_data['longitude']} {find_data['latitude']})"
        
        query = """
            INSERT INTO finds (find_number, site_id, material_type, object_type,
                             description, condition, depth, location, find_date,
                             excavation_date, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, ST_GeogFromText(%s), %s, %s, %s)
        """
        
        params = (
            find_data['find_number'],
            find_data['site_id'],
            find_data['material_type'],
            find_data.get('object_type'),
            find_data.get('description'),
            find_data.get('condition'),
            find_data.get('depth'),
            location,
            find_data['find_date'],
            find_data.get('excavation_date'),
            find_data.get('created_by')
        )
        
        return self.execute_insert(query, params)
    
    def update_find(self, find_id: int, find_data: Dict) -> bool:
        """Update find"""
        # Build dynamic update query
        fields = []
        params = []
        
        for key, value in find_data.items():
            if key not in ['id', 'created_at', 'updated_at', 'latitude', 'longitude']:
                fields.append(f"{key} = %s")
                params.append(value)
        
        # Handle location update
        if 'latitude' in find_data and 'longitude' in find_data:
            location = f"POINT({find_data['longitude']} {find_data['latitude']})"
            fields.append("location = ST_GeogFromText(%s)")
            params.append(location)
        
        params.append(find_id)
        
        query = f"""
            UPDATE finds 
            SET {', '.join(fields)}
            WHERE id = %s
        """
        
        return self.execute_update(query, tuple(params)) > 0
    
    def delete_find(self, find_id: int) -> bool:
        """Delete find"""
        query = "DELETE FROM finds WHERE id = %s"
        return self.execute_update(query, (find_id,)) > 0
    
    # Media methods
    def get_media_for_item(self, item_type: str, item_id: int) -> List[Dict]:
        """Get media for a specific item"""
        query = """
            SELECT m.*, mr.relation_type, mr.sort_order
            FROM media m
            JOIN media_relations mr ON m.id = mr.media_id
            WHERE mr.related_type = %s AND mr.related_id = %s
            ORDER BY mr.sort_order, m.created_at
        """
        return self.execute_query(query, (item_type, item_id))
    
    def add_media(self, media_data: Dict, related_type: str, related_id: int) -> int:
        """Add media and create relation"""
        self.connect()
        
        try:
            with self.connection.cursor() as cur:
                # Insert media
                cur.execute("""
                    INSERT INTO media (media_type, file_name, file_path, file_size,
                                     mime_type, description, photographer, capture_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    media_data['media_type'],
                    media_data['file_name'],
                    media_data['file_path'],
                    media_data.get('file_size'),
                    media_data.get('mime_type'),
                    media_data.get('description'),
                    media_data.get('photographer'),
                    media_data.get('capture_date')
                ))
                
                media_id = cur.fetchone()[0]
                
                # Create relation
                cur.execute("""
                    INSERT INTO media_relations (media_id, related_type, related_id)
                    VALUES (%s, %s, %s)
                """, (media_id, related_type, related_id))
                
                self.connection.commit()
                return media_id
                
        except Exception as e:
            self.connection.rollback()
            raise e
    
    def delete_media(self, media_id: int) -> bool:
        """Delete media (cascades to relations)"""
        query = "DELETE FROM media WHERE id = %s"
        return self.execute_update(query, (media_id,)) > 0
    
    # Worker methods
    def get_workers(self) -> List[Dict]:
        """Get all workers"""
        query = """
            SELECT id, full_name, role, telegram_username, email,
                   phone, certification_number, certification_expiry,
                   is_active, created_at, updated_at
            FROM workers
            ORDER BY full_name
        """
        return self.execute_query(query)
    
    def get_worker_by_telegram(self, telegram_username: str) -> Optional[Dict]:
        """Get worker by telegram username"""
        query = """
            SELECT id, full_name, role, telegram_username, email,
                   phone, certification_number, certification_expiry,
                   is_active
            FROM workers
            WHERE telegram_username = %s OR telegram_username = %s
        """
        username_with_at = f"@{telegram_username}" if not telegram_username.startswith('@') else telegram_username
        username_without_at = telegram_username.lstrip('@')
        
        results = self.execute_query(query, (username_with_at, username_without_at))
        return results[0] if results else None
    
    # Dive log methods
    def get_dive_logs(self, site_id: int = None) -> List[Dict]:
        """Get dive logs"""
        if site_id:
            query = """
                SELECT dl.*, s.site_code, s.site_name
                FROM dive_logs dl
                JOIN sites s ON dl.site_id = s.id
                WHERE dl.site_id = %s
                ORDER BY dl.dive_date DESC, dl.id DESC
            """
            return self.execute_query(query, (site_id,))
        else:
            query = """
                SELECT dl.*, s.site_code, s.site_name
                FROM dive_logs dl
                JOIN sites s ON dl.site_id = s.id
                ORDER BY dl.dive_date DESC, dl.id DESC
            """
            return self.execute_query(query)
    
    def add_dive_log(self, dive_data: Dict) -> int:
        """Add dive log"""
        query = """
            INSERT INTO dive_logs (site_id, dive_number, dive_date, dive_start,
                                 dive_end, max_depth, water_temp, visibility,
                                 current, dive_purpose, work_completed, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            dive_data['site_id'],
            dive_data['dive_number'],
            dive_data['dive_date'],
            dive_data['dive_start'],
            dive_data['dive_end'],
            dive_data.get('max_depth'),
            dive_data.get('water_temp'),
            dive_data.get('visibility'),
            dive_data.get('current'),
            dive_data.get('dive_purpose'),
            dive_data.get('work_completed'),
            dive_data.get('created_by')
        )
        
        return self.execute_insert(query, params)
    
    # Statistics methods
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        stats = {}
        
        # Sites count
        result = self.execute_query("SELECT COUNT(*) as count FROM sites")
        stats['total_sites'] = result[0]['count'] if result else 0
        
        # Finds count
        result = self.execute_query("SELECT COUNT(*) as count FROM finds")
        stats['total_finds'] = result[0]['count'] if result else 0
        
        # Media count
        result = self.execute_query("SELECT COUNT(*) as count FROM media")
        stats['total_media'] = result[0]['count'] if result else 0
        
        # Workers count
        result = self.execute_query("SELECT COUNT(*) as count FROM workers WHERE is_active = true")
        stats['active_workers'] = result[0]['count'] if result else 0
        
        # Dive logs count
        result = self.execute_query("SELECT COUNT(*) as count FROM dive_logs")
        stats['total_dives'] = result[0]['count'] if result else 0
        
        # Recent activity
        result = self.execute_query("""
            SELECT COUNT(*) as count 
            FROM finds 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        stats['finds_last_week'] = result[0]['count'] if result else 0
        
        return stats
    
    # Test connection
    def test_connection(self) -> tuple[bool, str]:
        """Test database connection"""
        try:
            self.connect()
            with self.connection.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                
                # Check PostGIS
                cur.execute("SELECT PostGIS_version()")
                postgis = cur.fetchone()[0]
                
                return True, f"PostgreSQL: {version}\nPostGIS: {postgis}"
        except Exception as e:
            return False, str(e)
    
    def __del__(self):
        """Cleanup connection on delete"""
        self.disconnect()
