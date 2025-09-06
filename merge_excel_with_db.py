#!/usr/bin/env python3
"""Merge Excel data with existing database finds"""

import pandas as pd
from supabase import create_client, Client
import os
import re

def get_supabase_client():
    """Get Supabase client"""
    url = "https://bqlmbmkffhzayinboanu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg"
    return create_client(url, key)

def load_excel_data():
    """Load Excel data"""
    excel_path = "/Users/enzo/Downloads/LAGOI 2024 FINDS.xlsx"
    if not os.path.exists(excel_path):
        print(f"Excel file not found: {excel_path}")
        return None
    
    df = pd.read_excel(excel_path)
    print(f"Loaded {len(df)} rows from Excel")
    return df

def load_database_finds():
    """Load existing finds from database"""
    supabase = get_supabase_client()
    response = supabase.table('finds').select("*").execute()
    db_finds = response.data
    print(f"Loaded {len(db_finds)} finds from database")
    
    # Create a mapping of find_number to find data
    finds_map = {}
    for find in db_finds:
        if find.get('find_number'):
            finds_map[find['find_number']] = find
    
    return db_finds, finds_map

def merge_data():
    """Merge Excel data with database finds"""
    # Load data
    df = load_excel_data()
    if df is None:
        return
    
    db_finds, finds_map = load_database_finds()
    
    # Create merged data
    merged_data = []
    updates = []
    
    print("\n=== Merging Data ===")
    
    # For each row in Excel, match with database find
    for idx, row in df.iterrows():
        # Generate the find_number that should correspond to this Excel row
        find_number = f"LAG2024-{idx+1:03d}"  # LAG2024-001, LAG2024-002, etc.
        
        if find_number in finds_map:
            # We have a match - prepare update data
            db_find = finds_map[find_number]
            update_data = {
                'id': db_find['id'],
                'find_number': find_number
            }
            
            # Map Excel fields to database fields
            # Storage location
            if pd.notna(row['STORAGE']):
                update_data['storage_location'] = str(row['STORAGE'])
            
            # Section (need to add this field to database)
            if pd.notna(row['SECTION']):
                update_data['section'] = str(row['SECTION'])
            
            # SU (Stratigraphic Unit - need to add this field)
            if pd.notna(row['SU']):
                update_data['su'] = str(row['SU'])
            
            # Quantity
            if pd.notna(row['QUANTITY']) and row['QUANTITY'] != 'complete':
                try:
                    update_data['quantity'] = int(row['QUANTITY'])
                except:
                    pass
            
            # Dimensions
            if pd.notna(row['DIMENSIONS']):
                update_data['dimensions'] = str(row['DIMENSIONS'])
            
            # Type -> material_type and object_type
            if pd.notna(row['TYPE']):
                type_str = str(row['TYPE'])
                # Try to split type into material and object
                if 'Ware' in type_str:
                    update_data['material_type'] = 'Ceramic'
                    update_data['object_type'] = type_str
                elif 'Mercury Jar' in type_str:
                    update_data['material_type'] = 'Ceramic'
                    update_data['object_type'] = 'Mercury Jar'
                elif 'Stone Ware' in type_str:
                    update_data['material_type'] = 'Stoneware'
                    update_data['object_type'] = type_str
            
            # Enhance description with Excel description
            excel_desc = str(row['DESCRIPTION']) if pd.notna(row['DESCRIPTION']) else ''
            if excel_desc and excel_desc != 'nan':
                # If we have existing description, append Excel description
                if db_find.get('description'):
                    update_data['description'] = f"{db_find['description']}\n\n[Excel Data]: {excel_desc}"
                else:
                    update_data['description'] = excel_desc
            
            # INV NO (inventory number - need to add this field)
            if pd.notna(row['INV NO']):
                update_data['inv_no'] = int(row['INV NO'])
            
            # Year
            if pd.notna(row['YEAR']):
                update_data['year'] = int(row['YEAR'])
            
            updates.append(update_data)
            print(f"  Matched: {find_number} - Will update with Excel data")
        else:
            print(f"  No match for row {idx+1} (would be {find_number})")
    
    print(f"\nTotal matches to update: {len(updates)}")
    
    # Create migration SQL for new fields
    migration_sql = """
-- Add new fields from Excel structure
ALTER TABLE finds ADD COLUMN IF NOT EXISTS inv_no INTEGER;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS section TEXT;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS su TEXT;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS storage_location TEXT;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS year INTEGER;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS quantity INTEGER;
ALTER TABLE finds ADD COLUMN IF NOT EXISTS dimensions TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_finds_inv_no ON finds(inv_no);
CREATE INDEX IF NOT EXISTS idx_finds_section ON finds(section);
CREATE INDEX IF NOT EXISTS idx_finds_year ON finds(year);
CREATE INDEX IF NOT EXISTS idx_finds_storage ON finds(storage_location);
"""
    
    # Save migration SQL
    migration_file = '/Users/enzo/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/shipwreck_excavation/database/migration_excel_fields.sql'
    with open(migration_file, 'w') as f:
        f.write(migration_sql)
    
    print(f"\n=== Migration SQL saved to: {migration_file} ===")
    print("Please apply this migration in Supabase SQL Editor before running the update.")
    
    # Save update data to CSV for review
    if updates:
        update_df = pd.DataFrame(updates)
        csv_path = '/Users/enzo/Downloads/finds_updates_from_excel.csv'
        update_df.to_csv(csv_path, index=False)
        print(f"\n=== Update data saved to: {csv_path} ===")
        print("Review this file before applying updates.")
        
        # Show sample of updates
        print("\n=== Sample Updates (first 5) ===")
        for update in updates[:5]:
            print(f"  {update['find_number']}: storage={update.get('storage_location', 'N/A')}, "
                  f"section={update.get('section', 'N/A')}, su={update.get('su', 'N/A')}")
    
    return updates

def apply_updates(updates):
    """Apply updates to database (after migration is done)"""
    if not updates:
        print("No updates to apply")
        return
    
    supabase = get_supabase_client()
    
    print(f"\n=== Applying {len(updates)} updates to database ===")
    
    success_count = 0
    error_count = 0
    
    for update in updates:
        try:
            find_id = update.pop('id')
            # Remove None values
            update = {k: v for k, v in update.items() if v is not None}
            
            # Update the find
            response = supabase.table('finds').update(update).eq('id', find_id).execute()
            success_count += 1
            print(f"  ✓ Updated {update['find_number']}")
        except Exception as e:
            error_count += 1
            print(f"  ✗ Error updating {update.get('find_number', 'unknown')}: {e}")
    
    print(f"\n=== Update Summary ===")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")

if __name__ == "__main__":
    print("=== Excel to Database Merge Tool ===")
    print("This tool will merge Excel data with existing database finds.\n")
    
    # First merge and prepare update data
    updates = merge_data()
    
    if updates:
        print("\n" + "="*50)
        print("IMPORTANT: Before applying updates:")
        print("1. Apply the migration SQL in Supabase SQL Editor")
        print("   File: database/migration_excel_fields.sql")
        print("2. Review the update data CSV")
        print("   File: /Users/enzo/Downloads/finds_updates_from_excel.csv")
        print("3. Run this script again with --apply flag to apply updates")
        print("="*50)
        
        # Check if user wants to apply now
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == '--apply':
            print("\nApplying updates...")
            apply_updates(updates)
        else:
            print("\nTo apply updates after migration, run:")
            print("python3 merge_excel_with_db.py --apply")
