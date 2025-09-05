"""
Database Factory - handles SQLite and PostgreSQL connections
"""

from PyQt5.QtCore import QSettings
import os

class DatabaseFactory:
    """Factory for creating appropriate database manager"""
    
    @staticmethod
    def create_database_manager(db_type: str = None):
        """Create database manager based on type"""
        settings = QSettings('Lagoi', 'ShipwreckExcavation')
        
        if not db_type:
            db_type = settings.value('database/type', 'supabase')
        
        if db_type == 'postgresql':
            from .pg_database_manager import PostgreSQLDatabaseManager
            connection_string = os.environ.get('SUPABASE_DB_URL',
                'postgresql://postgres.bqlmbmkffhzayinboanu:lagoi2025lagoi@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require')
            return PostgreSQLDatabaseManager(connection_string)
        elif db_type == 'supabase':
            from .supabase_database_manager import SupabaseDatabaseManager
            return SupabaseDatabaseManager()
        else:
            from .database_manager import DatabaseManager
            db_path = settings.value('database/path', '')
            return DatabaseManager(db_path)
    
    @staticmethod
    def get_connection_info(db_type: str = None) -> dict:
        """Get connection information"""
        settings = QSettings('Lagoi', 'ShipwreckExcavation')
        
        if not db_type:
            db_type = settings.value('database/type', 'supabase')
        
        if db_type == 'postgresql':
            return {
                'type': 'postgresql',
                'host': 'postgresql://postgres.bqlmbmkffhzayinboanu:lagoi2025lagoi@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require',
                'port': 5432,
                'database': 'postgres',
                'user': 'postgres',
                'sslmode': 'require'
            }
        elif db_type == 'supabase':
            return {
                'type': 'supabase',
                'url': 'https://bqlmbmkffhzayinboanu.supabase.co',
                'key': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg'
            }
        else:
            return {
                'type': 'sqlite',
                'path': settings.value('database/path', '')
            }
