#!/usr/bin/env python3
"""Export complete finds data with all fields to CSV"""

import pandas as pd
from supabase import create_client, Client
import os

def get_supabase_client():
    """Get Supabase client"""
    url = "https://bqlmbmkffhzayinboanu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg"
    return create_client(url, key)

def export_finds_with_excel_data():
    """Export finds with Excel data merged"""
    # Get current database data
    supabase = get_supabase_client()
    response = supabase.table('finds').select("*").order('find_number').execute()
    db_finds = response.data
    
    # Load Excel data
    excel_path = "/Users/enzo/Downloads/LAGOI 2024 FINDS.xlsx"
    df_excel = pd.read_excel(excel_path)
    
    # Create mapping for Excel data by row number
    excel_map = {}
    for idx, row in df_excel.iterrows():
        find_number = f"LAG2024-{idx+1:03d}"
        excel_map[find_number] = row
    
    # Merge data
    merged_data = []
    
    for find in db_finds:
        find_number = find.get('find_number')
        
        # Create row with database data
        row = {
            'find_number': find_number,
            'site_id': find.get('site_id'),
            'material_type': find.get('material_type'),
            'object_type': find.get('object_type'),
            'description': find.get('description'),
            'condition': find.get('condition'),
            'depth': find.get('depth'),
            'location': find.get('location'),
            'find_date': find.get('find_date'),
            'excavation_date': find.get('excavation_date'),
            'created_at': find.get('created_at'),
            'updated_at': find.get('updated_at')
        }
        
        # If we have matching Excel data, add those fields
        if find_number in excel_map:
            excel_row = excel_map[find_number]
            row['inv_no'] = excel_row['INV NO'] if pd.notna(excel_row['INV NO']) else None
            row['excel_location'] = excel_row['LOCATION']
            row['year'] = excel_row['YEAR']
            row['section'] = excel_row['SECTION'] if pd.notna(excel_row['SECTION']) else None
            row['su'] = excel_row['SU'] if pd.notna(excel_row['SU']) else None
            row['storage_location'] = excel_row['STORAGE'] if pd.notna(excel_row['STORAGE']) else None
            row['excel_type'] = excel_row['TYPE'] if pd.notna(excel_row['TYPE']) else None
            row['quantity'] = excel_row['QUANTITY'] if pd.notna(excel_row['QUANTITY']) else None
            row['dimensions'] = excel_row['DIMENSIONS'] if pd.notna(excel_row['DIMENSIONS']) else None
            row['excel_description'] = excel_row['DESCRIPTION'] if pd.notna(excel_row['DESCRIPTION']) else None
        else:
            # No Excel match - add empty columns
            row['inv_no'] = None
            row['excel_location'] = None
            row['year'] = None
            row['section'] = None
            row['su'] = None
            row['storage_location'] = None
            row['excel_type'] = None
            row['quantity'] = None
            row['dimensions'] = None
            row['excel_description'] = None
        
        merged_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(merged_data)
    
    # Reorder columns for better readability
    column_order = [
        'find_number', 'inv_no', 'year', 'site_id', 'excel_location',
        'material_type', 'object_type', 'excel_type',
        'section', 'su', 'storage_location',
        'quantity', 'dimensions', 'depth',
        'condition', 'location', 
        'description', 'excel_description',
        'find_date', 'excavation_date',
        'created_at', 'updated_at'
    ]
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    
    # Save to CSV
    output_path = "/Users/enzo/Downloads/finds_complete_merged.csv"
    df.to_csv(output_path, index=False)
    
    print(f"=== Exported Complete Finds Data ===")
    print(f"Total records: {len(df)}")
    print(f"Saved to: {output_path}")
    
    # Show statistics
    print("\n=== Statistics ===")
    
    # Material type distribution
    print("\nMaterial Types:")
    material_counts = df['material_type'].value_counts()
    for material, count in material_counts.items():
        print(f"  {material}: {count}")
    
    # Storage location distribution
    if 'storage_location' in df.columns:
        print("\nStorage Locations:")
        storage_counts = df['storage_location'].value_counts().head(10)
        for storage, count in storage_counts.items():
            print(f"  {storage}: {count}")
    
    # Section distribution
    if 'section' in df.columns:
        print("\nExcavation Sections (top 10):")
        section_counts = df['section'].value_counts().head(10)
        for section, count in section_counts.items():
            print(f"  {section}: {count}")
    
    # Year distribution
    if 'year' in df.columns:
        print("\nYears:")
        year_counts = df['year'].value_counts()
        for year, count in year_counts.items():
            print(f"  {year}: {count}")
    
    # Show sample records
    print("\n=== Sample Records (first 5 with Excel data) ===")
    sample = df[df['excel_type'].notna()].head(5)
    for idx, row in sample.iterrows():
        print(f"\n{row['find_number']}:")
        print(f"  Material: {row['material_type']}")
        print(f"  Excel Type: {row['excel_type']}")
        print(f"  Section: {row.get('section', 'N/A')}")
        print(f"  Storage: {row.get('storage_location', 'N/A')}")
        print(f"  SU: {row.get('su', 'N/A')}")
    
    return df

if __name__ == "__main__":
    df = export_finds_with_excel_data()
