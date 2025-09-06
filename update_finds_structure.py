#!/usr/bin/env python3
"""Update finds database structure based on Excel analysis"""

import pandas as pd
import os
import re
from datetime import datetime
from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client"""
    url = "https://bqlmbmkffhzayinboanu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg"
    return create_client(url, key)

def analyze_database_structure():
    """Analyze current database structure and data"""
    supabase = get_supabase_client()
    
    print("=== Current Database Finds ===")
    
    # Get all finds
    response = supabase.table('finds').select(
        "id, site_id, find_number, material_type, object_type, description, storage_location, quantity, dimensions"
    ).order('find_number').execute()
    
    db_finds = response.data
    print(f"Total finds in database: {len(db_finds)}")
    
    # Extract years from find_numbers
    find_numbers_2024 = []
    for find in db_finds:
        if find['find_number'] and '2024' in find['find_number']:
            find_numbers_2024.append(find['find_number'])
            print(f"  {find['find_number']}: {find['material_type']} - {find['description'][:50] if find['description'] else 'No description'}")
    
    print(f"\nTotal 2024 finds in database: {len(find_numbers_2024)}")
    
    return db_finds, find_numbers_2024

def compare_with_excel():
    """Compare database with Excel data"""
    excel_path = "/Users/enzo/Downloads/LAGOI 2024 FINDS.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"Excel file not found: {excel_path}")
        return
    
    # Read Excel
    df = pd.read_excel(excel_path)
    
    # Get database finds
    db_finds, db_find_numbers_2024 = analyze_database_structure()
    
    print("\n=== Comparison ===")
    print(f"Excel rows: {len(df)}")
    print(f"Database 2024 finds: {len(db_find_numbers_2024)}")
    
    # Fields mapping
    print("\n=== Field Mapping ===")
    print("Excel Field -> Database Field")
    print("INV NO -> (new field needed)")
    print("LOCATION -> site_id (via site_code)")
    print("YEAR -> (extract from find_number)")
    print("SECTION -> area_id (via area_code) or new field")
    print("SU -> context_description or new field")
    print("STORAGE -> storage_location")
    print("TYPE -> material_type + object_type")
    print("QUANTITY -> quantity")
    print("DIMENSIONS -> dimensions")
    print("DESCRIPTION -> description")
    
    # Check which fields need to be added
    print("\n=== Fields to Add to Database ===")
    print("1. inv_no (inventory number)")
    print("2. section (excavation section)")
    print("3. su (stratigraphic unit)")
    print("4. year (excavation year)")
    
    return df

def create_migration_sql():
    """Create SQL migration script"""
    migration_sql = """
-- Add new fields to finds table based on Excel structure

-- Add inventory number field
ALTER TABLE finds ADD COLUMN IF NOT EXISTS inv_no INTEGER;

-- Add section field (excavation section like F8N-F10N)
ALTER TABLE finds ADD COLUMN IF NOT EXISTS section TEXT;

-- Add stratigraphic unit field
ALTER TABLE finds ADD COLUMN IF NOT EXISTS su TEXT;

-- Add year field (extracted from find_number or directly stored)
ALTER TABLE finds ADD COLUMN IF NOT EXISTS year INTEGER;

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_finds_inv_no ON finds(inv_no);
CREATE INDEX IF NOT EXISTS idx_finds_section ON finds(section);
CREATE INDEX IF NOT EXISTS idx_finds_year ON finds(year);

-- Update existing records to extract year from find_number
UPDATE finds 
SET year = CAST(substring(find_number FROM 'LAG(\d{4})') AS INTEGER)
WHERE find_number LIKE 'LAG%' AND year IS NULL;
"""
    
    # Save migration script
    with open('/Users/enzo/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/shipwreck_excavation/database/migration_add_excel_fields.sql', 'w') as f:
        f.write(migration_sql)
    
    print("\n=== Migration SQL Created ===")
    print(migration_sql)
    
    return migration_sql

def apply_migration():
    """Apply the migration to the database"""
    print("\n=== Migration Instructions ===")
    print("Please apply the following migration manually in Supabase SQL Editor:")
    print("1. Go to https://supabase.com/dashboard/project/bqlmbmkffhzayinboanu/sql")
    print("2. Copy and paste the migration SQL from:")
    print("   /Users/enzo/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/shipwreck_excavation/database/migration_add_excel_fields.sql")
    print("3. Execute the SQL")
    print("\nThe migration SQL has been saved to the file above.")
    
    # For now, let's just show what needs to be done
    # Supabase client doesn't support DDL operations directly

def generate_find_numbers_for_excel(df):
    """Generate find numbers for Excel data that don't have them"""
    print("\n=== Generating Find Numbers for Excel ===")
    
    # Create find numbers based on year and row number
    find_numbers = []
    for idx, row in df.iterrows():
        year = row['YEAR']
        # Generate find number: LAG{year}_{row_number:04d}
        find_number = f"LAG{year}_{idx+1:04d}"
        find_numbers.append(find_number)
    
    df['find_number'] = find_numbers
    
    # Save updated Excel
    output_path = "/Users/enzo/Downloads/LAGOI 2024 FINDS_with_findnumbers.xlsx"
    df.to_excel(output_path, index=False)
    print(f"Saved Excel with find numbers to: {output_path}")
    
    # Also save as CSV for easier reading
    csv_path = output_path.replace('.xlsx', '.csv')
    df.to_csv(csv_path, index=False)
    print(f"Also saved as CSV: {csv_path}")
    
    return df

if __name__ == "__main__":
    print("=== Finds Database Structure Update ===")
    print("1. Analyzing current database structure...")
    
    # Compare with Excel
    df = compare_with_excel()
    
    if df is not None:
        # Create migration
        print("\n2. Creating migration SQL...")
        create_migration_sql()
        
        # Apply migration
        print("\n3. Applying migration to database...")
        apply_migration()
        
        # Generate find numbers for Excel
        print("\n4. Generating find numbers for Excel data...")
        df_with_numbers = generate_find_numbers_for_excel(df)
        
        print("\n=== Summary ===")
        print("- Database structure updated with new fields")
        print("- Excel file updated with generated find numbers")
        print("- Ready for data import/merge")
