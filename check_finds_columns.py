#!/usr/bin/env python3
"""Check finds table columns"""

from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client"""
    url = "https://bqlmbmkffhzayinboanu.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxbG1ibWtmZmh6YXlpbmJvYW51Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4NzYyNzUsImV4cCI6MjA3MjQ1MjI3NX0.namIzY2eLMuBwk_FRFWizFzhxyvySW-hl4tnYqAwUhg"
    return create_client(url, key)

if __name__ == "__main__":
    supabase = get_supabase_client()
    
    # Get one find to see all columns
    response = supabase.table('finds').select("*").limit(1).execute()
    
    if response.data:
        print("Columns in finds table:")
        for key in response.data[0].keys():
            print(f"  - {key}")
    else:
        print("No finds in database")
        
    # Try to get all finds with available columns
    print("\n=== Getting all finds ===")
    response = supabase.table('finds').select("*").execute()
    print(f"Total finds: {len(response.data)}")
    
    # Show find_numbers with 2024
    for find in response.data:
        if find.get('find_number') and '2024' in str(find.get('find_number', '')):
            print(f"  {find['find_number']}: {find.get('material_type', 'N/A')}")
