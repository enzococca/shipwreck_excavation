#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Supabase Media Operations
Verifies that media is correctly saved and retrieved from Supabase
"""

import os
import sys
from datetime import datetime

# Add plugin directory to Python path
plugin_dir = os.path.dirname(__file__)
if plugin_dir not in sys.path:
    sys.path.append(plugin_dir)

from database.supabase_database_manager import SupabaseDatabaseManager

def test_media_operations():
    """Test media operations on Supabase"""
    print("=" * 60)
    print("Testing Supabase Media Operations")
    print("=" * 60)
    print()
    
    # Create database manager
    db = SupabaseDatabaseManager()
    
    if not db.supabase:
        print("✗ Supabase client not available - check dependencies")
        return
    
    print("✓ Connected to Supabase")
    print()
    
    # Test 1: Query existing media
    print("Test 1: Query existing media")
    print("-" * 40)
    try:
        # Get all media
        result = db.supabase.table('media').select('*').limit(5).execute()
        if result.data:
            print(f"Found {len(result.data)} media records (showing max 5)")
            for media in result.data:
                print(f"  ID: {media['id']}, File: {media.get('file_name', 'N/A')}, Path: {media.get('file_path', 'N/A')}")
        else:
            print("No media records found")
    except Exception as e:
        print(f"Error querying media: {e}")
    print()
    
    # Test 2: Query media relations
    print("Test 2: Query media relations")
    print("-" * 40)
    try:
        result = db.supabase.table('media_relations').select('*').limit(5).execute()
        if result.data:
            print(f"Found {len(result.data)} media relations (showing max 5)")
            for rel in result.data:
                print(f"  Media ID: {rel['media_id']}, Type: {rel['related_type']}, Related ID: {rel['related_id']}")
        else:
            print("No media relations found")
    except Exception as e:
        print(f"Error querying relations: {e}")
    print()
    
    # Test 3: Test adding media (dry run - commented out to avoid adding test data)
    print("Test 3: Adding media (simulation)")
    print("-" * 40)
    
    test_media = {
        'media_type': 'photo',
        'file_name': 'test_photo.jpg',
        'file_path': 'media/photos/test_photo.jpg',
        'file_size': 1024,
        'description': 'Test media from script',
        'capture_date': datetime.now().isoformat()
    }
    
    print(f"Would add media: {test_media}")
    print("(Actual insertion commented out to avoid test data)")
    
    # Uncomment to actually test insertion:
    # try:
    #     media_id = db.add_media(test_media, 'find', 1)
    #     if media_id:
    #         print(f"✓ Media added with ID: {media_id}")
    #         # Clean up test data
    #         db.delete_media(media_id)
    #         print("✓ Test media cleaned up")
    #     else:
    #         print("✗ Failed to add media")
    # except Exception as e:
    #     print(f"✗ Error adding media: {e}")
    
    print()
    
    # Test 4: Check media for a specific site
    print("Test 4: Check media for sites")
    print("-" * 40)
    try:
        # Get first site with media
        sites_result = db.supabase.table('sites').select('id, name').limit(3).execute()
        if sites_result.data:
            for site in sites_result.data:
                site_id = site['id']
                site_name = site.get('name', f'Site {site_id}')
                
                # Use the get_media_for_site method
                media_list = db.get_media_for_site(site_id)
                if media_list:
                    print(f"Site '{site_name}' (ID: {site_id}): {len(media_list)} media files")
                    for media in media_list[:3]:  # Show max 3
                        print(f"    - {media.get('file_name', 'N/A')} ({media.get('related_type', 'N/A')})")
                else:
                    print(f"Site '{site_name}' (ID: {site_id}): No media")
        else:
            print("No sites found")
    except Exception as e:
        print(f"Error checking site media: {e}")
    
    print()
    print("=" * 60)
    print("Test completed")
    print("=" * 60)
    
    # Summary
    print("\nSummary:")
    print("- If media is saved in Google Drive but not showing in the plugin,")
    print("  check the console logs for 'ADD_MEDIA' messages")
    print("- Verify that media_relations table has correct entries")
    print("- Ensure the refresh_data() method is called after adding media")

if __name__ == "__main__":
    test_media_operations()