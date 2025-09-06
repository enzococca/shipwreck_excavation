#!/usr/bin/env python3
"""Export only 2024 finds data to CSV"""

import pandas as pd
from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client"""
    url = "https://bqlmbmkffhzayinboanu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg"
    return create_client(url, key)

def export_2024_finds():
    """Export only 2024 finds"""
    # Get database data - only 2024 finds
    supabase = get_supabase_client()
    response = supabase.table('finds').select("*").like('find_number', 'LAG2024%').order('find_number').execute()
    db_finds = response.data
    
    print(f"Found {len(db_finds)} finds from 2024")
    
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
            'material_type': find.get('material_type'),
            'object_type': find.get('object_type'),
            'description': find.get('description'),
            'condition': find.get('condition'),
            'depth': find.get('depth'),
            'location': find.get('location'),
            'find_date': find.get('find_date'),
            'excavation_date': find.get('excavation_date')
        }
        
        # Add Excel data if available
        if find_number in excel_map:
            excel_row = excel_map[find_number]
            row['inv_no'] = excel_row['INV NO'] if pd.notna(excel_row['INV NO']) else None
            row['year'] = excel_row['YEAR']
            row['section'] = excel_row['SECTION'] if pd.notna(excel_row['SECTION']) else None
            row['su'] = str(excel_row['SU']) if pd.notna(excel_row['SU']) else None
            row['storage_location'] = excel_row['STORAGE'] if pd.notna(excel_row['STORAGE']) else None
            row['excel_type'] = excel_row['TYPE'] if pd.notna(excel_row['TYPE']) else None
            row['quantity'] = excel_row['QUANTITY'] if pd.notna(excel_row['QUANTITY']) else None
            row['dimensions'] = excel_row['DIMENSIONS'] if pd.notna(excel_row['DIMENSIONS']) else None
            row['excel_description'] = excel_row['DESCRIPTION'] if pd.notna(excel_row['DESCRIPTION']) else None
        
        merged_data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(merged_data)
    
    # Reorder columns for better readability
    column_order = [
        'find_number', 'inv_no', 'year',
        'material_type', 'excel_type', 'object_type',
        'section', 'su', 'storage_location',
        'quantity', 'dimensions', 'depth',
        'condition', 'location',
        'description', 'excel_description',
        'find_date', 'excavation_date'
    ]
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    
    # Save to CSV
    output_path = "/Users/enzo/Downloads/LAGOI_2024_FINDS_COMPLETE.csv"
    df.to_csv(output_path, index=False)
    
    print(f"\n=== Exported 2024 Finds Only ===")
    print(f"Total records: {len(df)}")
    print(f"Saved to: {output_path}")
    
    # Verify all 175 are there
    print("\n=== Verification ===")
    print(f"Excel has: {len(df_excel)} rows")
    print(f"Database has: {len(df)} LAG2024 finds")
    
    if len(df) == len(df_excel):
        print("✓ Perfect match! All 175 finds are present.")
    else:
        print(f"⚠ Mismatch: Excel has {len(df_excel)}, database has {len(df)}")
    
    # Show statistics
    print("\n=== Material Type Distribution ===")
    material_counts = df['material_type'].value_counts()
    for material, count in material_counts.head(10).items():
        print(f"  {material}: {count}")
    
    # Storage locations
    print("\n=== Storage Locations ===")
    storage_counts = df['storage_location'].value_counts()
    for storage, count in storage_counts.head(10).items():
        print(f"  {storage}: {count}")
    
    # Sections
    print("\n=== Top Excavation Sections ===")
    section_counts = df['section'].value_counts()
    for section, count in section_counts.head(10).items():
        print(f"  {section}: {count}")
    
    # Check for missing data
    print("\n=== Data Completeness ===")
    print(f"  With inventory number: {df['inv_no'].notna().sum()}/{len(df)}")
    print(f"  With section: {df['section'].notna().sum()}/{len(df)}")
    print(f"  With storage location: {df['storage_location'].notna().sum()}/{len(df)}")
    print(f"  With dimensions: {df['dimensions'].notna().sum()}/{len(df)}")
    print(f"  With Excel description: {df['excel_description'].notna().sum()}/{len(df)}")
    
    return df

if __name__ == "__main__":
    df = export_2024_finds()
