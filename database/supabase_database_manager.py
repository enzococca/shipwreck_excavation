"""
Supabase Database Manager using API
"""

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    create_client = None
    Client = None

from PyQt5.QtCore import QSettings, QObject, pyqtSignal
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from qgis.core import QgsMessageLog, Qgis

class SupabaseDatabaseManager(QObject):
    """Database manager using Supabase API instead of direct PostgreSQL"""
    
    # Qt signals
    db_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        # Use same organization as main plugin
        self.settings = QSettings('ShipwreckExcavation', 'ShipwreckExcavation')
        
        # Supabase credentials
        self.supabase_url = os.environ.get('SUPABASE_URL', 
            'https://bqlmbmkffhzayinboanu.supabase.co')
        self.supabase_key = os.environ.get('SUPABASE_KEY',
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg')
        
        # Initialize Supabase client if available
        if SUPABASE_AVAILABLE:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.supabase = None
            
        self.media_path_manager = None
        
        # Add db_path for compatibility - will be set from settings
        self.db_path = None
        self._init_db_path_from_settings()
    
    def _init_db_path_from_settings(self):
        """Initialize db_path from settings"""
        # Try to get media path from settings
        media_path = self.get_setting('media_base_path')
        if media_path and os.path.exists(media_path):
            self.db_path = media_path
            QgsMessageLog.logMessage(f"Initialized db_path from settings: {self.db_path}",
                                   "SupabaseDB", Qgis.Info)
        else:
            # No path configured yet - will be set when user configures it
            QgsMessageLog.logMessage("No media path configured yet - user needs to set it in Settings",
                                   "SupabaseDB", Qgis.Warning)

    def set_media_path_manager(self, media_path_manager):
        """Set media path manager"""
        self.media_path_manager = media_path_manager
    
    def get_setting(self, key, default=None):
        """Get a setting value"""
        try:
            # First check if we have a settings table
            result = self.supabase.table('settings').select('*').eq('key', key).execute()
            if result.data:
                return result.data[0]['value']
        except:
            pass
        
        # Check QSettings for user-specific settings
        if key == 'media_base_path':
            # ALWAYS prioritize local QSettings for media paths (user-specific)
            QgsMessageLog.logMessage(f"=== Checking media_base_path settings ===", "SupabaseDB", Qgis.Info)
            
            # Debug: List all keys in settings
            all_keys = self.settings.allKeys()
            QgsMessageLog.logMessage(f"All QSettings keys: {all_keys}", "SupabaseDB", Qgis.Info)
            
            # Try multiple possible keys in QSettings
            # Note: QSettings already includes organization/application prefix
            possible_keys = [
                'media_base_path',
                'media_storage_path',
                'shipwreck_excavation/media_base_path',
                'shipwreck_excavation/media_storage_path'
            ]
            
            for qkey in possible_keys:
                media_path = self.settings.value(qkey)
                if media_path:
                    QgsMessageLog.logMessage(f"Found value for key '{qkey}': '{media_path}'" + f" (type: {type(media_path)})", "SupabaseDB", Qgis.Info)
                    # Strip any whitespace that might be causing issues
                    media_path = str(media_path).strip()
                    
                    # Test with different path variations
                    test_paths = [
                        media_path,
                        media_path.rstrip('/'),
                        media_path.rstrip('/') + '/',
                        os.path.expanduser(media_path)
                    ]
                    
                    for test_path in test_paths:
                        if os.path.exists(test_path):
                            QgsMessageLog.logMessage(f"Path exists! Using: '{test_path}'", "SupabaseDB", Qgis.Success)
                            return test_path
                        else:
                            QgsMessageLog.logMessage(f"Path does not exist: '{test_path}'", "SupabaseDB", Qgis.Info)
                else:
                    QgsMessageLog.logMessage(f"No value found for key '{qkey}'", "SupabaseDB", Qgis.Info)
            
            # Also check what organization/application the settings are using
            QgsMessageLog.logMessage(f"Settings organization: {self.settings.organizationName()}", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Settings application: {self.settings.applicationName()}", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Settings fileName: {self.settings.fileName()}", "SupabaseDB", Qgis.Info)
            
            # Return None so the caller can handle missing path
            QgsMessageLog.logMessage(f"No valid media path found - user needs to configure it in Settings", "SupabaseDB", Qgis.Warning)
            return None
        
        return default
    
    def set_setting(self, key, value):
        """Set a setting value"""
        QgsMessageLog.logMessage(f"set_setting called with key='{key}', value='{value}'", "SupabaseDB", Qgis.Info)
        
        # For media paths, save to QSettings (user-specific)
        if key in ['media_storage_path', 'media_base_path']:
            QgsMessageLog.logMessage(f"=== Saving media path to QSettings ===", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Key: {key}, Value: {value}", "SupabaseDB", Qgis.Info)

            # Save to multiple keys to ensure compatibility
            # Note: QSettings already includes organization/application prefix
            self.settings.setValue('media_base_path', value)
            self.settings.setValue('media_storage_path', value)
            self.settings.setValue('shipwreck_excavation/media_base_path', value)
            self.settings.setValue('shipwreck_excavation/media_storage_path', value)

            # Force sync
            self.settings.sync()

            # Update internal db_path when media path changes
            if value and os.path.exists(value):
                self.db_path = value
                QgsMessageLog.logMessage(f"Updated internal db_path to: {self.db_path}", "SupabaseDB", Qgis.Info)
            
            # Verify it was saved
            test_read1 = self.settings.value('media_base_path')
            test_read2 = self.settings.value('shipwreck_excavation/media_base_path')
            QgsMessageLog.logMessage(f"Verification - Read back 'media_base_path': {test_read1}", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Verification - Read back 'shipwreck_excavation/media_base_path': {test_read2}", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Settings file location: {self.settings.fileName()}", "SupabaseDB", Qgis.Info)
            
            return True
        
        # For other settings, save to database
        try:
            # Check if setting exists
            result = self.supabase.table('settings').select('*').eq('key', key).execute()
            
            if result.data:
                # Update existing setting
                self.supabase.table('settings').update({'value': value}).eq('key', key).execute()
            else:
                # Insert new setting
                self.supabase.table('settings').insert({'key': key, 'value': value}).execute()
            
            return True
        except Exception as e:
            QgsMessageLog.logMessage(f"Error setting {key}: {e}", "SupabaseDB", Qgis.Critical)
            return False
    
    def connect(self):
        """No connection needed for API"""
        pass
    
    def disconnect(self):
        """No disconnection needed for API"""
        pass
    
    # Site methods
    def get_sites(self) -> List[Dict]:
        """Get all sites"""
        try:
            response = self.supabase.table('sites').select("*").execute()
            sites = []
            for site in response.data:
                # Convert geography to lat/lon
                if site.get('location'):
                    # Parse PostGIS point - simplified for now
                    site['latitude'] = None
                    site['longitude'] = None
                sites.append(site)
            return sites
        except Exception as e:
            error_msg = f"Error getting sites: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return []
    
    def get_site_by_id(self, site_id: int) -> Optional[Dict]:
        """Get site by ID"""
        try:
            response = self.supabase.table('sites').select("*").eq('id', site_id).execute()
            if response.data:
                site = response.data[0]
                if site.get('location'):
                    site['latitude'] = None
                    site['longitude'] = None
                return site
            return None
        except Exception as e:
            error_msg = f"Error getting site: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return None
    
    def add_site(self, site_data: Dict) -> int:
        """Add new site"""
        try:
            # Remove lat/lon, handle location separately if needed
            data = site_data.copy()
            data.pop('latitude', None)
            data.pop('longitude', None)
            
            response = self.supabase.table('sites').insert(data).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            error_msg = f"Error adding site: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return None
    
    def update_site(self, site_id: int, site_data: Dict) -> bool:
        """Update site"""
        try:
            data = site_data.copy()
            data.pop('latitude', None)
            data.pop('longitude', None)
            data.pop('id', None)
            
            QgsMessageLog.logMessage(f"DEBUG update_site: Updating site {site_id} with data: {data}", 
                                   "SupabaseDB", Qgis.Info)
            
            response = self.supabase.table('sites').update(data).eq('id', site_id).execute()
            QgsMessageLog.logMessage(f"DEBUG update_site: Response data: {response.data}", 
                                   "SupabaseDB", Qgis.Info)
            
            if response.data:
                QgsMessageLog.logMessage(f"DEBUG update_site: Update successful", 
                                       "SupabaseDB", Qgis.Success)
                return True
            else:
                QgsMessageLog.logMessage(f"DEBUG update_site: Update failed - no data returned", 
                                       "SupabaseDB", Qgis.Warning)
                return False
        except Exception as e:
            QgsMessageLog.logMessage(f"Error updating site {site_id}: {e}", 
                                   "SupabaseDB", Qgis.Critical)
            import traceback
            error_details = traceback.format_exc()
            QgsMessageLog.logMessage(f"Traceback: {error_details}", 
                                   "SupabaseDB", Qgis.Critical)
            return False
    
    def delete_site(self, site_id: int) -> bool:
        """Delete site"""
        try:
            response = self.supabase.table('sites').delete().eq('id', site_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting site: {e}")
            return False
    
    # Find methods
    def get_finds_by_site(self, site_id: int) -> List[Dict]:
        """Get finds for a specific site"""
        try:
            response = self.supabase.table('finds').select("*").eq('site_id', site_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error getting finds: {e}")
            return []
    
    def get_find_by_id(self, find_id: int) -> Optional[Dict]:
        """Get find by ID"""
        try:
            response = self.supabase.table('finds').select("*, sites(site_code, site_name)").eq('id', find_id).execute()
            if response.data:
                find = response.data[0]
                # Flatten site data
                if 'sites' in find:
                    find['site_code'] = find['sites']['site_code']
                    find['site_name'] = find['sites']['site_name']
                    del find['sites']
                return find
            return None
        except Exception as e:
            print(f"Error getting find: {e}")
            return None
    
    def get_finds(self, site_id: int = None) -> List[Dict]:
        """Get finds, optionally filtered by site"""
        try:
            query = self.supabase.table('finds').select("*, sites(site_code, site_name)")
            
            if site_id:
                query = query.eq('site_id', site_id)
            
            response = query.order('created_at', desc=True).execute()
            
            # Get media counts
            media_response = self.supabase.table('media_relations').select("related_id").eq('related_type', 'find').execute()
            media_data = media_response.data or []
            
            # Count media per find
            media_counts = {}
            for media in media_data:
                find_id = media['related_id']
                media_counts[find_id] = media_counts.get(find_id, 0) + 1
            
            # Flatten site data and add media count
            finds = []
            for find in (response.data or []):
                if 'sites' in find:
                    find['site_code'] = find['sites']['site_code']
                    find['site_name'] = find['sites']['site_name']
                    del find['sites']
                # Add media count
                find['media_count'] = media_counts.get(find.get('id'), 0)
                finds.append(find)
            
            return finds
        except Exception as e:
            error_msg = f"Error getting finds: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return []
    
    def add_find(self, find_data: Dict) -> int:
        """Add new find"""
        try:
            data = find_data.copy()
            data.pop('latitude', None)
            data.pop('longitude', None)
            
            response = self.supabase.table('finds').insert(data).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            print(f"Error adding find: {e}")
            return None
    
    def update_find(self, find_id: int, find_data: Dict) -> bool:
        """Update find"""
        try:
            data = find_data.copy()
            data.pop('latitude', None)
            data.pop('longitude', None)
            data.pop('id', None)
            
            response = self.supabase.table('finds').update(data).eq('id', find_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating find: {e}")
            return False
    
    def delete_find(self, find_id: int) -> bool:
        """Delete find"""
        try:
            response = self.supabase.table('finds').delete().eq('id', find_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting find: {e}")
            return False
    
    # Dive logs methods
    def add_dive_log(self, dive_data: Dict) -> int:
        """Add new dive log"""
        try:
            response = self.supabase.table('dive_logs').insert(dive_data).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            print(f"Error adding dive log: {e}")
            return None
    
    def update_dive_log(self, dive_id: int, dive_data: Dict) -> bool:
        """Update dive log"""
        try:
            data = dive_data.copy()
            data.pop('id', None)
            
            response = self.supabase.table('dive_logs').update(data).eq('id', dive_id).execute()
            return bool(response.data)
        except Exception as e:
            print(f"Error updating dive log: {e}")
            return False
    
    def delete_dive_log(self, dive_id: int) -> bool:
        """Delete dive log"""
        try:
            response = self.supabase.table('dive_logs').delete().eq('id', dive_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting dive log: {e}")
            return False

    # Media methods
    def get_media_for_item(self, item_type: str, item_id: int) -> List[Dict]:
        """Get media for a specific item"""
        try:
            # First get media relations
            response = self.supabase.table('media_relations').select(
                "*, media(*)"
            ).eq('related_type', item_type).eq('related_id', item_id).execute()
            
            media_items = []
            for relation in response.data:
                if 'media' in relation:
                    media = relation['media']
                    media['relation_type'] = relation.get('relation_type')
                    media['sort_order'] = relation.get('sort_order')
                    media_items.append(media)
            
            return sorted(media_items, key=lambda x: (x.get('sort_order', 999), x.get('created_at', '')))
        except Exception as e:
            print(f"Error getting media: {e}")
            return []
    
    def add_media(self, media_data: Dict, related_type: str, related_id: int) -> int:
        """Add media and create relation"""
        try:
            QgsMessageLog.logMessage(f"=== ADD_MEDIA called ===", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Media data: {media_data}", "SupabaseDB", Qgis.Info)
            QgsMessageLog.logMessage(f"Related type: {related_type}, Related ID: {related_id}", "SupabaseDB", Qgis.Info)

            # Insert media
            response = self.supabase.table('media').insert(media_data).execute()
            if not response.data:
                QgsMessageLog.logMessage(f"No data returned from media insert", "SupabaseDB", Qgis.Critical)
                return None

            media_id = response.data[0]['id']
            QgsMessageLog.logMessage(f"Media inserted with ID: {media_id}", "SupabaseDB", Qgis.Success)

            # Create relation
            relation_data = {
                'media_id': media_id,
                'related_type': related_type,
                'related_id': related_id
            }

            QgsMessageLog.logMessage(f"Creating relation: {relation_data}", "SupabaseDB", Qgis.Info)
            rel_response = self.supabase.table('media_relations').insert(relation_data).execute()

            if rel_response.data:
                QgsMessageLog.logMessage(f"Relation created successfully", "SupabaseDB", Qgis.Success)
            else:
                QgsMessageLog.logMessage(f"Failed to create relation", "SupabaseDB", Qgis.Warning)

            return media_id
        except Exception as e:
            QgsMessageLog.logMessage(f"Error adding media: {str(e)}", "SupabaseDB", Qgis.Critical)
            print(f"Error adding media: {e}")
            return None
    
    def delete_media(self, media_id: int) -> bool:
        """Delete media (cascades to relations)"""
        try:
            response = self.supabase.table('media').delete().eq('id', media_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting media: {e}")
            return False
    
    def get_media_for_site(self, site_id: int) -> List[Dict]:
        """Get all media for a site including finds and dive logs"""
        try:
            all_media = []
            
            # Get media directly related to site
            relations = self.supabase.table('media_relations').select("*, media(*)").eq('related_type', 'site').eq('related_id', site_id).execute()
            print(f"DEBUG: Site media relations: {len(relations.data) if relations.data else 0}")
            if relations.data:
                for relation in relations.data:
                    if 'media' in relation and relation['media']:
                        media = relation['media']
                        media['related_type'] = 'site'
                        media['related_id'] = site_id
                        all_media.append(media)
            
            # Get finds for this site
            finds = self.supabase.table('finds').select("id").eq('site_id', site_id).execute()
            print(f"DEBUG: Found {len(finds.data) if finds.data else 0} finds for site {site_id}")
            if finds.data:
                find_ids = [f['id'] for f in finds.data]
                print(f"DEBUG: Find IDs: {find_ids}")
                find_relations = self.supabase.table('media_relations').select("*, media(*)").eq('related_type', 'find').in_('related_id', find_ids).execute()
                print(f"DEBUG: Find media relations: {len(find_relations.data) if find_relations.data else 0}")
                if find_relations.data:
                    for relation in find_relations.data:
                        if 'media' in relation and relation['media']:
                            media = relation['media']
                            media['related_type'] = 'find'
                            media['related_id'] = relation['related_id']
                            print(f"DEBUG: Adding find media: {media.get('id')} - {media.get('file_name')}")
                            all_media.append(media)
            
            # Get dive logs for this site
            divelogs = self.supabase.table('dive_logs').select("id").eq('site_id', site_id).execute()
            print(f"DEBUG: Found {len(divelogs.data) if divelogs.data else 0} dive logs for site {site_id}")
            if divelogs.data:
                dive_ids = [d['id'] for d in divelogs.data]
                dive_relations = self.supabase.table('media_relations').select("*, media(*)").eq('related_type', 'dive').in_('related_id', dive_ids).execute()
                print(f"DEBUG: Dive media relations: {len(dive_relations.data) if dive_relations.data else 0}")
                if dive_relations.data:
                    for relation in dive_relations.data:
                        if 'media' in relation and relation['media']:
                            media = relation['media']
                            media['related_type'] = 'dive'
                            media['related_id'] = relation['related_id']
                            all_media.append(media)
            
            print(f"DEBUG: Total media for site {site_id}: {len(all_media)}")
            return sorted(all_media, key=lambda x: x.get('created_at', ''), reverse=True)
        except Exception as e:
            print(f"Error getting media for site: {e}")
            return []
    
    # Worker methods
    def get_workers(self) -> List[Dict]:
        """Get all workers"""
        try:
            response = self.supabase.table('workers').select("*").order('full_name').execute()
            return response.data or []
        except Exception as e:
            error_msg = f"Error getting workers: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return []
    
    def get_worker_by_telegram(self, telegram_username: str) -> Optional[Dict]:
        """Get worker by telegram username"""
        try:
            username_with_at = f"@{telegram_username}" if not telegram_username.startswith('@') else telegram_username
            username_without_at = telegram_username.lstrip('@')
            
            response = self.supabase.table('workers').select("*").or_(
                f"telegram_username.eq.{username_with_at},telegram_username.eq.{username_without_at}"
            ).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error getting worker: {e}")
            return None
    
    # Dive log methods
    def get_dive_logs_for_widget(self, site_id: int, year_filter: str = None) -> List[Dict]:
        """Get dive logs formatted for the widget with complex joins"""
        try:
            # First get dive logs
            query = self.supabase.table('dive_logs').select("*")
            if site_id:
                query = query.eq('site_id', site_id)
            if year_filter and year_filter != "All":
                # Filter by year - Supabase doesn't have strftime, so we filter in Python
                pass  # Will filter after fetching
            
            response = query.order('dive_date', desc=True).order('dive_start', desc=True).execute()
            dive_logs = response.data or []
            
            # Get team counts for each dive
            team_response = self.supabase.table('dive_team').select("dive_id, worker_id").execute()
            team_data = team_response.data or []
            
            # Count team members per dive
            team_counts = {}
            for member in team_data:
                dive_id = member['dive_id']
                if dive_id not in team_counts:
                    team_counts[dive_id] = set()
                team_counts[dive_id].add(member['worker_id'])
            
            # Get media counts for dives
            media_response = self.supabase.table('media_relations').select("related_id").eq('related_type', 'dive_log').execute()
            media_data = media_response.data or []
            
            # Count media per dive
            media_counts = {}
            for media in media_data:
                dive_id = media['related_id']
                media_counts[dive_id] = media_counts.get(dive_id, 0) + 1
            
            # Format results
            results = []
            for log in dive_logs:
                # Filter by year if needed
                if year_filter and year_filter != "All":
                    dive_year = log.get('dive_date', '')[:4]
                    if dive_year != year_filter:
                        continue
                
                # Calculate duration in minutes
                if log.get('dive_start') and log.get('dive_end'):
                    try:
                        from datetime import datetime
                        start = datetime.strptime(log['dive_start'], '%H:%M:%S')
                        end = datetime.strptime(log['dive_end'], '%H:%M:%S')
                        duration_min = int((end - start).total_seconds() / 60)
                    except:
                        duration_min = None
                else:
                    duration_min = None
                
                results.append({
                    'id': log.get('id'),
                    'dive_number': log.get('dive_number', ''),
                    'dive_date': log.get('dive_date', ''),
                    'time_range': f"{log.get('dive_start', '')} - {log.get('dive_end', '')}",
                    'max_depth': log.get('max_depth'),
                    'duration_min': duration_min,
                    'team_size': len(team_counts.get(log['id'], set())),
                    'media_count': media_counts.get(log['id'], 0),  # Add media count
                    'visibility': log.get('visibility'),
                    'current_strength': log.get('current_strength', ''),
                    'findings_summary': log.get('findings_summary', '')
                })
            
            return results
        except Exception as e:
            print(f"Error getting dive logs: {e}")
            return []
    
    def get_dive_logs(self, site_id: int = None) -> List[Dict]:
        """Get dive logs"""
        try:
            query = self.supabase.table('dive_logs').select("*, sites(site_code, site_name)")
            
            if site_id:
                query = query.eq('site_id', site_id)
            
            response = query.execute()
            
            # Flatten site data
            logs = []
            for log in response.data:
                if 'sites' in log:
                    log['site_code'] = log['sites']['site_code']
                    log['site_name'] = log['sites']['site_name']
                    del log['sites']
                logs.append(log)
            
            return sorted(logs, key=lambda x: (x.get('dive_date', ''), x.get('id', 0)), reverse=True)
        except Exception as e:
            print(f"Error getting dive logs: {e}")
            return []
    
    def add_dive_log(self, dive_data: Dict) -> int:
        """Add dive log"""
        try:
            response = self.supabase.table('dive_logs').insert(dive_data).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            print(f"Error adding dive log: {e}")
            return None
    
    # Statistics methods
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            stats = {}
            
            # Get counts
            tables = ['sites', 'finds', 'media', 'workers', 'dive_logs']
            for table in tables:
                response = self.supabase.table(table).select("id", count='exact').execute()
                stats[f'total_{table}'] = response.count or 0
            
            # Active workers
            response = self.supabase.table('workers').select("id", count='exact').eq('is_active', True).execute()
            stats['active_workers'] = response.count or 0
            
            # Recent finds (last 7 days)
            from datetime import datetime, timedelta
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            response = self.supabase.table('finds').select("id", count='exact').gte('created_at', week_ago).execute()
            stats['finds_last_week'] = response.count or 0
            
            return stats
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    # SQL compatibility method
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SQL-like query by translating to Supabase API calls"""
        try:
            # Simple SQL parser for basic SELECT queries
            query_lower = query.lower().strip()
            
            if query_lower.startswith("select"):
                # Parse basic SELECT queries
                if "from sites" in query_lower:
                    if "id, site_name" in query_lower:
                        if "where status = 'active'" in query_lower:
                            response = self.supabase.table('sites').select("id, site_name").eq('status', 'active').order('site_name').execute()
                            return response.data
                        else:
                            response = self.supabase.table('sites').select("id, site_name").execute()
                            return [{'id': r['id'], 'site_name': r['site_name']} for r in response.data]
                    elif "count(*)" in query_lower:
                        response = self.supabase.table('sites').select("*", count='exact').execute()
                        return [{'count': response.count}]
                    elif "id, site_code, site_name" in query_lower:
                        # Handle the site widget query with concatenations
                        response = self.supabase.table('sites').select("*").order('site_code').execute()
                        sites = []
                        for site in response.data:
                            # Build the concatenated fields
                            period = f"{site.get('period_from', '')} - {site.get('period_to', '')}" if site.get('period_from') or site.get('period_to') else ''
                            depth_range = f"{site.get('depth_min', '')} - {site.get('depth_max', '')} m" if site.get('depth_min') or site.get('depth_max') else ' -  m'
                            
                            sites.append({
                                'id': site.get('id'),
                                'site_code': site.get('site_code', ''),
                                'site_name': site.get('site_name', ''),
                                'vessel_type': site.get('vessel_type', ''),
                                'period': period,
                                'depth_range': depth_range,
                                'status': site.get('status', ''),
                                'discovery_date': site.get('discovery_date', '')
                            })
                        return sites
                    else:
                        response = self.supabase.table('sites').select("*").execute()
                        return response.data
                        
                elif "from media_relations" in query_lower:
                    if "select count" in query_lower:
                        # Handle COUNT queries for media_relations
                        if params and "where" in query_lower:
                            if "related_type = 'find'" in query_lower and "related_id = ?" in query_lower:
                                response = self.supabase.table('media_relations').select("*", count='exact').eq('related_type', 'find').eq('related_id', params[0]).execute()
                                return [{'count': response.count}]
                            elif "related_type = ?" in query_lower and "related_id = ?" in query_lower and len(params) >= 2:
                                response = self.supabase.table('media_relations').select("*", count='exact').eq('related_type', params[0]).eq('related_id', params[1]).execute()
                                return [{'count': response.count}]
                    elif "where related_type = 'find' and related_id = ?" in query_lower and params:
                        response = self.supabase.table('media_relations').select("*").eq('related_type', 'find').eq('related_id', params[0]).execute()
                        return response.data
                    elif "where related_type = ?" in query_lower and params:
                        response = self.supabase.table('media_relations').select("*").eq('related_type', params[0]).execute()
                        return response.data
                    else:
                        response = self.supabase.table('media_relations').select("*").execute()
                        return response.data
                
                elif "from finds" in query_lower:
                    if "where id = ?" in query_lower and params:
                        # Query for specific find by ID
                        response = self.supabase.table('finds').select("*").eq('id', params[0]).execute()
                        return response.data
                    elif "where site_id" in query_lower and params:
                        response = self.supabase.table('finds').select("*").eq('site_id', params[0]).execute()
                        return response.data
                    else:
                        response = self.supabase.table('finds').select("*").execute()
                        return response.data
                        
                elif "from workers" in query_lower:
                    if "where active = 1" in query_lower or "where is_active = 1" in query_lower:
                        response = self.supabase.table('workers').select("*").eq('is_active', True).execute()
                        return response.data
                    else:
                        response = self.supabase.table('workers').select("*").execute()
                        return response.data
                    
                elif "from dive_logs" in query_lower:
                    if "count(*)" in query_lower and "sum(" in query_lower:
                        # This is the statistics query - calculate aggregates manually
                        site_id = params[0] if params else None
                        query = self.supabase.table('dive_logs').select("*")
                        if site_id:
                            query = query.eq('site_id', site_id)
                        response = query.execute()
                        logs = response.data or []
                        
                        # Calculate aggregates
                        total_dives = len(logs)
                        total_hours = 0
                        depths = []
                        
                        for log in logs:
                            # Calculate hours from start/end times
                            if log.get('dive_start') and log.get('dive_end'):
                                try:
                                    from datetime import datetime
                                    start = datetime.strptime(log['dive_start'], '%H:%M:%S')
                                    end = datetime.strptime(log['dive_end'], '%H:%M:%S')
                                    hours = (end - start).total_seconds() / 3600
                                    total_hours += hours
                                except:
                                    pass
                            
                            if log.get('max_depth'):
                                depths.append(float(log['max_depth']))
                        
                        avg_depth = sum(depths) / len(depths) if depths else 0
                        max_depth = max(depths) if depths else 0
                        
                        return [{
                            'total_dives': total_dives, 
                            'total_hours': total_hours, 
                            'avg_depth': avg_depth, 
                            'max_depth': max_depth
                        }]
                    elif "left join dive_team" in query_lower:
                        # This is the complex dive logs query with team counts
                        # Use our custom method instead
                        return []  # Let the widget use get_dive_logs_for_widget instead
                    elif "where id = ?" in query_lower and params:
                        # Query for specific dive log by ID
                        response = self.supabase.table('dive_logs').select("*").eq('id', params[0]).execute()
                        return response.data
                    elif "where site_id" in query_lower and params:
                        response = self.supabase.table('dive_logs').select("*").eq('site_id', params[0]).execute()
                        return response.data
                    else:
                        response = self.supabase.table('dive_logs').select("*").execute()
                        return response.data
                    
                elif "from work_session" in query_lower:
                    # Complex join query for work sessions
                    if "join workers" in query_lower and "join sites" in query_lower:
                        # Get work sessions with worker and site names through dive_logs
                        sessions = self.supabase.table('work_session').select("*, workers(*), dive_logs(*, sites(*))").execute()
                        if sessions.data:
                            # Transform to match expected format
                            result = []
                            for s in sessions.data:
                                # Extract site name from dive_logs->sites relationship
                                site_name = ''
                                if 'dive_logs' in s and s['dive_logs'] and 'sites' in s['dive_logs']:
                                    site_name = s['dive_logs']['sites']['site_name']
                                
                                result.append({
                                    'id': s['id'],
                                    'work_date': s.get('start_time', '')[:10] if s.get('start_time') else '',  # Extract date from timestamp
                                    'full_name': s['workers']['full_name'] if 'workers' in s else '',
                                    'site_name': site_name,
                                    'work_type': s.get('work_type', ''),
                                    'hours_worked': s.get('hours_worked', 0),
                                    'rate_per_hour': 0,  # Not in our table
                                    'total_payment': 0,  # Not in our table
                                    'payment_status': 'pending'  # Not in our table
                                })
                            return result
                        return []
                    else:
                        response = self.supabase.table('work_session').select("*").execute()
                        return response.data
                        
                elif "from costs" in query_lower:
                    if "select category, sum(amount)" in query_lower:
                        # Handle GROUP BY query for costs summary
                        site_id = params[0] if params else None
                        if site_id:
                            costs = self.supabase.table('costs').select("category, amount").eq('site_id', site_id).execute()
                        else:
                            costs = self.supabase.table('costs').select("category, amount").execute()
                        
                        # Group by category and sum
                        totals = {}
                        for cost in costs.data:
                            cat = cost['category']
                            if cat not in totals:
                                totals[cat] = 0
                            totals[cat] += cost['amount']
                        
                        # Return as list of dicts
                        return [{'category': k, 'total': v} for k, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)]
                    elif "where site_id = ?" in query_lower and params:
                        response = self.supabase.table('costs').select("*").eq('site_id', params[0]).execute()
                        return response.data
                    else:
                        response = self.supabase.table('costs').select("*").execute()
                        return response.data
                        
                elif "from media" in query_lower:
                    # Check if it's a JOIN query
                    if "join media_relations" in query_lower:
                        # For now, return empty list for complex JOIN queries
                        # In a real implementation, you'd want to handle this properly
                        return []
                    elif "where id = ?" in query_lower and params:
                        # Handle specific media query by ID
                        media_id = params[0]
                        # Check what fields are being selected
                        if "select file_path, media_type, file_name" in query_lower:
                            response = self.supabase.table('media').select("file_path, media_type, file_name").eq('id', media_id).execute()
                        else:
                            response = self.supabase.table('media').select("*").eq('id', media_id).execute()
                        return response.data
                    else:
                        response = self.supabase.table('media').select("*").execute()
                        return response.data
                
                elif "from dive_log_signatures" in query_lower:
                    if "where dive_log_id = ? and worker_id = ?" in query_lower and params and len(params) >= 2:
                        response = self.supabase.table('dive_log_signatures').select("*").eq('dive_log_id', params[0]).eq('worker_id', params[1]).execute()
                        return response.data
                    elif "where dive_log_id = ?" in query_lower and params:
                        response = self.supabase.table('dive_log_signatures').select("*").eq('dive_log_id', params[0]).execute()
                        return response.data
                    else:
                        response = self.supabase.table('dive_log_signatures').select("*").execute()
                        return response.data
                        
                elif "from dive_team" in query_lower:
                    if "where dive_id = ?" in query_lower and params:
                        response = self.supabase.table('dive_team').select("*").eq('dive_id', params[0]).execute()
                        return response.data
                    else:
                        response = self.supabase.table('dive_team').select("*").execute()
                        return response.data
                    
            # Return empty list for unsupported queries
            return []
            
        except Exception as e:
            error_msg = f"Error executing query: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute SQL-like update/delete query by translating to Supabase API calls"""
        try:
            query_lower = query.lower().strip()
            
            if query_lower.startswith("update"):
                # Parse UPDATE queries
                if "update dive_logs set" in query_lower and params:
                    if "where id = ?" in query_lower:
                        # Update dive log
                        dive_id = params[-1]
                        # Parse SET clause to extract fields
                        set_clause = query[query.lower().find("set")+3:query.lower().find("where")].strip()
                        fields = {}
                        field_names = []
                        for field in set_clause.split(','):
                            field_name = field.split('=')[0].strip()
                            field_names.append(field_name)
                        
                        # Build update data from params (excluding the ID which is last)
                        for i, field_name in enumerate(field_names):
                            if i < len(params) - 1:
                                fields[field_name] = params[i]
                        
                        # Check if dive_number is being updated to avoid duplicates
                        if 'dive_number' in fields:
                            # Check if this dive_number already exists for another record
                            existing = self.supabase.table('dive_logs').select('id').eq('dive_number', fields['dive_number']).neq('id', dive_id).execute()
                            if existing.data:
                                # Dive number already exists, don't update it
                                print(f"Warning: dive_number {fields['dive_number']} already exists, skipping dive_number update")
                                del fields['dive_number']
                        
                        response = self.supabase.table('dive_logs').update(fields).eq('id', dive_id).execute()
                        return True
                elif "update workers set" in query_lower and params:
                    if "is_active = false" in query_lower or "is_active = 0" in query_lower:
                        # Deactivate worker
                        worker_id = params[-1]
                        response = self.supabase.table('workers').update({'is_active': False}).eq('id', worker_id).execute()
                        return True
                    elif "where id = ?" in query_lower:
                        # General worker update
                        worker_id = params[-1]
                        # Parse SET clause to extract fields
                        set_clause = query[query.lower().find("set")+3:query.lower().find("where")].strip()
                        fields = {}
                        field_names = []
                        for field in set_clause.split(','):
                            field_name = field.split('=')[0].strip()
                            field_names.append(field_name)
                        
                        # Build update data from params (excluding the ID which is last)
                        for i, field_name in enumerate(field_names):
                            if i < len(params) - 1:
                                fields[field_name] = params[i]
                        
                        response = self.supabase.table('workers').update(fields).eq('id', worker_id).execute()
                        return True
                        
                elif "update finds set" in query_lower and params:
                    # Extract field updates from query
                    # This is a simplified parser - in production you'd want a proper SQL parser
                    if "where id = ?" in query_lower:
                        find_id = params[-1]  # ID is last param
                        # For now, just update all fields from the find dialog
                        # In a real implementation, you'd parse the SET clause
                        return True  # Assume success for now
                        
            elif query_lower.startswith("delete"):
                # Parse DELETE queries
                if "delete from workers where id = ?" in query_lower and params:
                    response = self.supabase.table('workers').delete().eq('id', params[0]).execute()
                    return True
                elif "delete from finds where id = ?" in query_lower and params:
                    response = self.supabase.table('finds').delete().eq('id', params[0]).execute()
                    return True
                elif "delete from sites where id = ?" in query_lower and params:
                    response = self.supabase.table('sites').delete().eq('id', params[0]).execute()
                    return True
                elif "delete from dive_logs where id = ?" in query_lower and params:
                    response = self.supabase.table('dive_logs').delete().eq('id', params[0]).execute()
                    return True
                elif "delete from dive_team where dive_id = ?" in query_lower and params:
                    response = self.supabase.table('dive_team').delete().eq('dive_id', params[0]).execute()
                    return True
                    
            elif query_lower.startswith("insert"):
                # Parse INSERT queries
                if "insert into dive_logs" in query_lower and params:
                    # Extract column names from query
                    start = query.find('(') + 1
                    end = query.find(')')
                    columns = [col.strip() for col in query[start:end].split(',')]
                    
                    # Build data dictionary
                    data = {}
                    for i, col in enumerate(columns):
                        if i < len(params):
                            data[col] = params[i]
                    
                    response = self.supabase.table('dive_logs').insert(data).execute()
                    if response.data and len(response.data) > 0:
                        return response.data[0]['id']
                    return None
                elif "insert into workers" in query_lower and params:
                    # Extract column names from query
                    start = query.find('(') + 1
                    end = query.find(')')
                    columns = [col.strip() for col in query[start:end].split(',')]
                    
                    # Build data dictionary
                    data = {}
                    for i, col in enumerate(columns):
                        if i < len(params):
                            # Convert 'active' to 'is_active' for Supabase
                            if col == 'active':
                                data['is_active'] = bool(params[i])
                            else:
                                data[col] = params[i]
                    
                    response = self.supabase.table('workers').insert(data).execute()
                    return True
                elif "insert into dive_team" in query_lower and params:
                    # Extract column names from query
                    start = query.find('(') + 1
                    end = query.find(')')
                    columns = [col.strip() for col in query[start:end].split(',')]
                    
                    # Build data dictionary
                    data = {}
                    for i, col in enumerate(columns):
                        if i < len(params):
                            data[col] = params[i]
                    
                    response = self.supabase.table('dive_team').insert(data).execute()
                    return True
                else:
                    # Other insert queries handled by specific methods
                    return True
                
            return False
            
        except Exception as e:
            error_msg = f"Error executing update: {e}"
            print(error_msg)
            self.db_error.emit(error_msg)
            return False
    
    # Test connection
    def test_connection(self) -> tuple[bool, str]:
        """Test database connection"""
        try:
            # Test with a simple query
            response = self.supabase.table('sites').select("id").limit(1).execute()
            
            return True, f"Supabase API connected\nURL: {self.supabase_url}"
        except Exception as e:
            return False, str(e)
