#!/usr/bin/env python3
"""Fix material types based on Excel data"""

import pandas as pd
from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client"""
    url = "https://bqlmbmkffhzayinboanu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg"
    return create_client(url, key)

def map_type_to_material(excel_type):
    """Map Excel TYPE to proper material_type"""
    if pd.isna(excel_type):
        return None
    
    type_str = str(excel_type).strip()
    
    # Create mapping based on Excel types
    if 'Stone Ware' in type_str:
        return 'Stoneware'
    elif 'Black Ware' in type_str or 'Red Ware' in type_str:
        return 'Black/Red Ware'
    elif 'Celadon' in type_str:
        return 'Celadon'
    elif 'Porcelain' in type_str:
        return 'Porcelain'
    elif 'Martaban' in type_str:
        return 'Martaban'
    elif 'Mercury Jar' in type_str:
        return 'Mercury Jar'
    elif 'Glass' in type_str:
        return 'Glass'
    elif 'Metal' in type_str or 'Coin' in type_str or 'Lead' in type_str or 'hook' in type_str:
        return 'Metal'
    elif 'Wood' in type_str:
        return 'Wood'
    elif 'Bone' in type_str:
        return 'Bone'
    elif 'Shell' in type_str or 'Opercula' in type_str or 'Mother of pearl' in type_str:
        return 'Shell/Pearl'
    elif 'Stone tool' in type_str or 'Stone weight' in type_str or 'Pestle' in type_str:
        return 'Stone Tool'
    elif 'Rope' in type_str or 'Woven Fiber' in type_str:
        return 'Fiber/Rope'
    elif 'Nut' in type_str or 'Seed' in type_str or 'Coconut' in type_str:
        return 'Organic (Nut/Seed)'
    elif 'Resin' in type_str:
        return 'Resin'
    elif 'Horn' in type_str:
        return 'Horn'
    elif 'Clay' in type_str:
        return 'Clay'
    elif 'Sediment' in type_str:
        return 'Sediment'
    elif 'Organic' in type_str:
        return 'Organic Material'
    elif 'Weight' in type_str:
        return 'Weight'
    elif 'Local Production' in type_str:
        return 'Local Production'
    else:
        return 'Unknown'

def fix_materials():
    """Fix material types in database based on Excel"""
    # Load Excel
    excel_path = "/Users/enzo/Downloads/LAGOI 2024 FINDS.xlsx"
    df = pd.read_excel(excel_path)
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Get all finds
    response = supabase.table('finds').select('id, find_number, material_type').execute()
    finds_map = {f['find_number']: f for f in response.data if f.get('find_number')}
    
    print("=== Updating Material Types ===")
    
    updates = []
    material_counts = {}
    
    # For each Excel row, update corresponding database find
    for idx, row in df.iterrows():
        find_number = f"LAG2024-{idx+1:03d}"
        
        if find_number in finds_map:
            excel_type = row['TYPE']
            new_material = map_type_to_material(excel_type)
            
            if new_material:
                db_find = finds_map[find_number]
                current_material = db_find.get('material_type')
                
                if current_material != new_material:
                    updates.append({
                        'id': db_find['id'],
                        'find_number': find_number,
                        'old_material': current_material,
                        'new_material': new_material,
                        'excel_type': excel_type
                    })
                
                # Count materials
                material_counts[new_material] = material_counts.get(new_material, 0) + 1
    
    print(f"\nTotal updates needed: {len(updates)}")
    
    # Show material distribution
    print("\n=== New Material Distribution ===")
    for mat, count in sorted(material_counts.items()):
        print(f"  {mat}: {count} items")
    
    # Show some examples
    print("\n=== Sample Updates (first 10) ===")
    for update in updates[:10]:
        print(f"  {update['find_number']}: {update['old_material']} -> {update['new_material']} (Excel: {update['excel_type']}")
    
    # Apply updates
    if updates:
        print("\n=== Applying Updates ===")
        success = 0
        errors = 0
        
        for update in updates:
            try:
                response = supabase.table('finds').update({
                    'material_type': update['new_material'],
                    'object_type': update['excel_type']  # Also store original TYPE as object_type
                }).eq('id', update['id']).execute()
                success += 1
                print(f"  ✓ Updated {update['find_number']}")
            except Exception as e:
                errors += 1
                print(f"  ✗ Error updating {update['find_number']}: {e}")
        
        print(f"\n=== Summary ===")
        print(f"  Successful updates: {success}")
        print(f"  Errors: {errors}")
    
    return updates

if __name__ == "__main__":
    print("=== Material Type Fix Tool ===")
    updates = fix_materials()
    
    if updates:
        # Save update log
        df_updates = pd.DataFrame(updates)
        csv_path = '/Users/enzo/Downloads/material_type_updates.csv'
        df_updates.to_csv(csv_path, index=False)
        print(f"\nUpdate log saved to: {csv_path}")
