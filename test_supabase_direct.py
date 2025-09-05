#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Supabase Direct Connection
Tests Supabase media operations without QGIS dependencies
"""

import os
from datetime import datetime

try:
    from supabase import create_client
    print("✓ Supabase module installed")
except ImportError:
    print("✗ Supabase module not installed - run: pip install supabase")
    exit(1)

# Supabase credentials (same as in the plugin)
SUPABASE_URL = 'https://bqlmbmkffhzayinboanu.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg'

def test_direct_connection():
    """Test direct Supabase connection"""
    print("=" * 60)
    print("Testing Direct Supabase Connection")
    print("=" * 60)
    print()
    
    # Connect to Supabase
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✓ Connected to Supabase")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    print()
    
    # Test 1: Count records in tables
    print("Table Record Counts:")
    print("-" * 40)
    tables = ['sites', 'finds', 'media', 'media_relations', 'dive_logs', 'workers']
    for table in tables:
        try:
            result = supabase.table(table).select('id', count='exact').execute()
            print(f"  {table}: {result.count if hasattr(result, 'count') else len(result.data)} records")
        except Exception as e:
            print(f"  {table}: Error - {e}")
    print()
    
    # Test 2: Recent media additions
    print("Recent Media Additions (last 5):")
    print("-" * 40)
    try:
        result = supabase.table('media').select('*').order('id', desc=True).limit(5).execute()
        if result.data:
            for media in result.data:
                print(f"  ID: {media['id']}")
                print(f"    File: {media.get('file_name', 'N/A')}")
                print(f"    Path: {media.get('file_path', 'N/A')}")
                print(f"    Type: {media.get('media_type', 'N/A')}")
                print(f"    Size: {media.get('file_size', 0)} bytes")
                print()
        else:
            print("  No media records found")
    except Exception as e:
        print(f"  Error: {e}")
    print()
    
    # Test 3: Media relations
    print("Recent Media Relations (last 5):")
    print("-" * 40)
    try:
        result = supabase.table('media_relations').select('*').order('id', desc=True).limit(5).execute()
        if result.data:
            for rel in result.data:
                print(f"  Media {rel['media_id']} → {rel['related_type']} {rel['related_id']}")
        else:
            print("  No media relations found")
    except Exception as e:
        print(f"  Error: {e}")
    print()
    
    # Test 4: Finds with media
    print("Finds with Media:")
    print("-" * 40)
    try:
        # Get finds that have media relations
        relations = supabase.table('media_relations').select('related_id').eq('related_type', 'find').execute()
        if relations.data:
            find_ids = list(set([r['related_id'] for r in relations.data]))[:5]  # Unique, max 5
            
            # Get find details
            finds = supabase.table('finds').select('*').in_('id', find_ids).execute()
            if finds.data:
                for find in finds.data:
                    print(f"  Find {find['find_number']} (ID: {find['id']})")
                    
                    # Get media for this find
                    media_rels = supabase.table('media_relations').select('*, media(*)').eq('related_type', 'find').eq('related_id', find['id']).execute()
                    if media_rels.data:
                        for rel in media_rels.data:
                            if 'media' in rel and rel['media']:
                                print(f"    - {rel['media'].get('file_name', 'N/A')}")
        else:
            print("  No finds with media found")
    except Exception as e:
        print(f"  Error: {e}")
    
    print()
    print("=" * 60)
    print("Test completed")
    print()
    print("If media files are saved in Google Drive but not showing in the database:")
    print("1. Check that the add_media() method is being called correctly")
    print("2. Verify that media_relations entries are created")
    print("3. Ensure refresh_data() is called after adding media")
    print("4. Check QGIS logs for 'ADD_MEDIA' messages")

if __name__ == "__main__":
    test_direct_connection()